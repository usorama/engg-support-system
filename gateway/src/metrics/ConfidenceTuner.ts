/**
 * Confidence Tuner - Deterministic Weight Optimization
 *
 * Analyzes query feedback to compute optimal confidence weights.
 * Runs periodically (cron) or on-demand to tune the confidence formula.
 *
 * The tuner computes correlations between:
 * - Feedback outcomes (useful, not_useful, partial)
 * - Confidence factors (semantic score, structural presence, citation coverage)
 *
 * Based on correlations, it recommends weight adjustments.
 */

import * as fs from "fs";
import * as path from "path";
import { QueryMetricsStore, type QueryMetric } from "./QueryMetrics.js";

// ============================================================================
// Types
// ============================================================================

/**
 * Current confidence weights
 */
export interface ConfidenceWeights {
  semanticScore: number;
  structuralPresence: number;
  citationCoverage: number;
}

/**
 * Confidence thresholds
 */
export interface ConfidenceThresholds {
  high: number;
  medium: number;
  low: number;
}

/**
 * Full confidence config
 */
export interface ConfidenceConfig {
  version: number;
  updatedAt: string;
  updatedBy: string;
  weights: ConfidenceWeights;
  thresholds: ConfidenceThresholds;
  behavior: {
    belowLow: string;
    belowMedium: string;
  };
}

/**
 * Correlation result for a single factor
 */
export interface FactorCorrelation {
  /** Factor name */
  factor: string;
  /** Correlation with "useful" feedback (-1 to 1) */
  usefulCorrelation: number;
  /** Average value for useful responses */
  avgWhenUseful: number;
  /** Average value for not_useful responses */
  avgWhenNotUseful: number;
  /** Suggested weight adjustment (-0.1 to 0.1) */
  suggestedAdjustment: number;
}

/**
 * Weight update recommendation
 */
export interface WeightRecommendation {
  /** Timestamp of analysis */
  timestamp: string;
  /** Number of metrics analyzed */
  metricsAnalyzed: number;
  /** Useful responses count */
  usefulCount: number;
  /** Not useful responses count */
  notUsefulCount: number;
  /** Per-factor correlations */
  correlations: FactorCorrelation[];
  /** Recommended new weights */
  newWeights: ConfidenceWeights;
  /** Overall confidence in the recommendation (0-1) */
  confidence: number;
  /** Whether to auto-apply (confidence > 0.8) */
  autoApply: boolean;
}

// ============================================================================
// Confidence Tuner
// ============================================================================

/**
 * Confidence Tuner - Analyzes feedback and recommends weight adjustments
 */
export class ConfidenceTuner {
  private metricsStore: QueryMetricsStore;
  private configPath: string;

  constructor(metricsStore: QueryMetricsStore, configPath?: string) {
    this.metricsStore = metricsStore;
    this.configPath = configPath ?? path.join(
      path.dirname(new URL(import.meta.url).pathname),
      "../config/confidence-weights.json"
    );
  }

  /**
   * Load current weights from config
   */
  loadCurrentWeights(): ConfidenceConfig {
    try {
      const data = fs.readFileSync(this.configPath, "utf-8");
      return JSON.parse(data) as ConfidenceConfig;
    } catch {
      // Return defaults
      return {
        version: 1,
        updatedAt: new Date().toISOString(),
        updatedBy: "default",
        weights: {
          semanticScore: 0.7,
          structuralPresence: 0.1,
          citationCoverage: 0.2,
        },
        thresholds: {
          high: 0.8,
          medium: 0.5,
          low: 0.3,
        },
        behavior: {
          belowLow: "warn",
          belowMedium: "include_raw",
        },
      };
    }
  }

  /**
   * Compute optimal weights based on feedback data
   *
   * Algorithm:
   * 1. Load metrics with feedback from last 7 days
   * 2. Separate useful vs not_useful responses
   * 3. Compute correlation: factor value ↔ feedback outcome
   * 4. Adjust weights based on correlation strength
   */
  async computeOptimalWeights(): Promise<WeightRecommendation> {
    // Get metrics with feedback
    const metricsWithFeedback = await this.metricsStore.getMetricsWithFeedback(500);

    // Separate by feedback type
    const useful = metricsWithFeedback.filter((m) => m.feedback === "useful");
    const notUseful = metricsWithFeedback.filter((m) => m.feedback === "not_useful");

    // Need minimum samples for meaningful analysis
    const minSamples = 10;
    if (useful.length < minSamples || notUseful.length < minSamples) {
      const currentConfig = this.loadCurrentWeights();
      return {
        timestamp: new Date().toISOString(),
        metricsAnalyzed: metricsWithFeedback.length,
        usefulCount: useful.length,
        notUsefulCount: notUseful.length,
        correlations: [],
        newWeights: currentConfig.weights,
        confidence: 0,
        autoApply: false,
      };
    }

    // Compute correlations for each factor
    const correlations: FactorCorrelation[] = [
      this.computeFactorCorrelation("semanticScore", useful, notUseful, (m) => m.avgSemanticScore),
      this.computeFactorCorrelation("structuralPresence", useful, notUseful, (m) =>
        m.structuralMatchCount > 0 ? 1 : 0
      ),
      this.computeFactorCorrelation("citationCoverage", useful, notUseful, (m) =>
        Math.min(m.citationCount / 3, 1)
      ),
    ];

    // Current weights
    const currentConfig = this.loadCurrentWeights();
    const currentWeights = currentConfig.weights;

    // Apply adjustments (bounded to prevent wild swings)
    const newWeights: ConfidenceWeights = {
      semanticScore: this.boundWeight(
        currentWeights.semanticScore +
          (correlations.find((c) => c.factor === "semanticScore")?.suggestedAdjustment ?? 0)
      ),
      structuralPresence: this.boundWeight(
        currentWeights.structuralPresence +
          (correlations.find((c) => c.factor === "structuralPresence")?.suggestedAdjustment ?? 0)
      ),
      citationCoverage: this.boundWeight(
        currentWeights.citationCoverage +
          (correlations.find((c) => c.factor === "citationCoverage")?.suggestedAdjustment ?? 0)
      ),
    };

    // Normalize weights to sum to 1.0
    const weightSum = newWeights.semanticScore + newWeights.structuralPresence + newWeights.citationCoverage;
    newWeights.semanticScore = newWeights.semanticScore / weightSum;
    newWeights.structuralPresence = newWeights.structuralPresence / weightSum;
    newWeights.citationCoverage = newWeights.citationCoverage / weightSum;

    // Calculate overall confidence in recommendations
    const avgCorrelationStrength =
      correlations.reduce((sum, c) => sum + Math.abs(c.usefulCorrelation), 0) / correlations.length;
    const sampleSizeConfidence = Math.min((useful.length + notUseful.length) / 100, 1);
    const overallConfidence = avgCorrelationStrength * sampleSizeConfidence;

    return {
      timestamp: new Date().toISOString(),
      metricsAnalyzed: metricsWithFeedback.length,
      usefulCount: useful.length,
      notUsefulCount: notUseful.length,
      correlations,
      newWeights,
      confidence: overallConfidence,
      autoApply: overallConfidence > 0.8,
    };
  }

  /**
   * Compute correlation for a single factor
   */
  private computeFactorCorrelation(
    factorName: string,
    useful: QueryMetric[],
    notUseful: QueryMetric[],
    extractValue: (m: QueryMetric) => number
  ): FactorCorrelation {
    // Calculate averages
    const avgWhenUseful =
      useful.length > 0
        ? useful.reduce((sum, m) => sum + extractValue(m), 0) / useful.length
        : 0;

    const avgWhenNotUseful =
      notUseful.length > 0
        ? notUseful.reduce((sum, m) => sum + extractValue(m), 0) / notUseful.length
        : 0;

    // Correlation: how much does the factor differ between useful and not_useful?
    // Range: -1 (higher value = worse) to 1 (higher value = better)
    const diff = avgWhenUseful - avgWhenNotUseful;
    const maxDiff = Math.max(avgWhenUseful, avgWhenNotUseful, 0.01); // Avoid division by zero
    const correlation = Math.max(-1, Math.min(1, diff / maxDiff));

    // Suggested adjustment based on correlation
    // Strong positive correlation → increase weight
    // Strong negative correlation → decrease weight
    // Max adjustment: ±0.1
    const suggestedAdjustment = correlation * 0.1;

    return {
      factor: factorName,
      usefulCorrelation: correlation,
      avgWhenUseful,
      avgWhenNotUseful,
      suggestedAdjustment,
    };
  }

  /**
   * Bound weight to valid range (0.05 to 0.9)
   */
  private boundWeight(weight: number): number {
    return Math.max(0.05, Math.min(0.9, weight));
  }

  /**
   * Apply recommended weights to config file
   */
  async applyWeights(recommendation: WeightRecommendation): Promise<void> {
    const currentConfig = this.loadCurrentWeights();

    const newConfig: ConfidenceConfig = {
      version: currentConfig.version + 1,
      updatedAt: new Date().toISOString(),
      updatedBy: "confidence-tuner",
      weights: recommendation.newWeights,
      thresholds: currentConfig.thresholds,
      behavior: currentConfig.behavior,
    };

    fs.writeFileSync(this.configPath, JSON.stringify(newConfig, null, 2));
    console.log(`[ConfidenceTuner] Applied new weights: ${JSON.stringify(recommendation.newWeights)}`);
  }

  /**
   * Save recommendation to file for human review
   */
  saveRecommendation(recommendation: WeightRecommendation, outputPath?: string): void {
    const filePath = outputPath ?? "/tmp/ess-weight-recommendations.json";
    fs.writeFileSync(filePath, JSON.stringify(recommendation, null, 2));
    console.log(`[ConfidenceTuner] Saved recommendation to ${filePath}`);
  }

  /**
   * Run full tuning cycle
   *
   * 1. Compute optimal weights from feedback
   * 2. If confidence > 0.8, auto-apply
   * 3. Otherwise, save for human review
   */
  async runTuningCycle(autoApplyThreshold = 0.8): Promise<WeightRecommendation> {
    console.log("[ConfidenceTuner] Starting tuning cycle...");

    const recommendation = await this.computeOptimalWeights();

    console.log(`[ConfidenceTuner] Analyzed ${recommendation.metricsAnalyzed} metrics`);
    console.log(`[ConfidenceTuner] Useful: ${recommendation.usefulCount}, Not useful: ${recommendation.notUsefulCount}`);
    console.log(`[ConfidenceTuner] Confidence: ${(recommendation.confidence * 100).toFixed(1)}%`);

    if (recommendation.confidence >= autoApplyThreshold && recommendation.usefulCount >= 10) {
      console.log("[ConfidenceTuner] High confidence - applying weights automatically");
      await this.applyWeights(recommendation);
    } else {
      console.log("[ConfidenceTuner] Low confidence - saving for human review");
      this.saveRecommendation(recommendation);
    }

    return recommendation;
  }
}

// ============================================================================
// CLI Entry Point (for cron jobs)
// ============================================================================

/**
 * Run tuning from command line
 * Usage: node dist/metrics/ConfidenceTuner.js
 */
async function main(): Promise<void> {
  const metricsStore = new QueryMetricsStore(7);
  const tuner = new ConfidenceTuner(metricsStore);

  try {
    const recommendation = await tuner.runTuningCycle();
    console.log("\n=== Recommendation Summary ===");
    console.log(JSON.stringify(recommendation, null, 2));
  } catch (error) {
    console.error("[ConfidenceTuner] Error:", error);
    process.exit(1);
  } finally {
    await metricsStore.close();
  }
}

// Run if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

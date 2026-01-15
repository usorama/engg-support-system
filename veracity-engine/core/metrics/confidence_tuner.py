"""
ML-Based Confidence Tuning for Self-Learning System.

Analyzes query feedback to automatically adjust confidence scoring weights
using deterministic ML techniques (linear regression, moving averages).

This module provides:
- Correlation analysis between metrics and user satisfaction
- Weight adjustment recommendations based on feedback patterns
- Deterministic ML (no neural networks, reproducible results)
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import statistics

from neo4j import GraphDatabase

from core.config import get_config
from core.metrics.query_metrics import QueryMetrics

logger = logging.getLogger(__name__)


class ConfidenceTuner:
    """
    ML-based confidence score tuner.

    Analyzes feedback patterns and recommends weight adjustments
    for improving confidence score accuracy.
    """

    def __init__(self, neo4j_uri: Optional[str] = None,
                 neo4j_user: Optional[str] = None,
                 neo4j_password: Optional[str] = None):
        """
        Initialize confidence tuner.

        Args:
            neo4j_uri: Neo4j connection URI (optional, uses config if not provided)
            neo4j_user: Neo4j username (optional, uses config if not provided)
            neo4j_password: Neo4j password (optional, uses config if not provided)
        """
        self.metrics = QueryMetrics(neo4j_uri, neo4j_user, neo4j_password)
        self.driver = self.metrics.driver

    def analyze_feedback(
        self,
        time_window_hours: int = 24,
        project: Optional[str] = None,
        min_feedback_samples: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze feedback patterns to identify tuning opportunities.

        Args:
            time_window_hours: Hours to analyze (default: 24)
            project: Filter by project (optional)
            min_feedback_samples: Minimum feedback samples required for analysis

        Returns:
            Analysis results dictionary with:
                - feedback_distribution: Counts by rating
                - confidence_correlation: Correlation between confidence and usefulness
                - false_positive_rate: Queries with high confidence but 'not_useful' feedback
                - false_negative_rate: Queries with low confidence but 'useful' feedback
                - recommendations: List of tuning recommendations
        """
        # Get metrics with feedback
        metrics = self.metrics.get_metrics(
            time_window_hours=time_window_hours,
            project=project,
            has_feedback=True
        )

        if len(metrics) < min_feedback_samples:
            logger.warning(f"Insufficient feedback samples: {len(metrics)} < {min_feedback_samples}")
            return {
                "status": "insufficient_data",
                "sample_count": len(metrics),
                "min_required": min_feedback_samples,
                "recommendations": ["Collect more user feedback before tuning"]
            }

        # Categorize by feedback
        useful_queries = [m for m in metrics if m['user_feedback'] == 'useful']
        not_useful_queries = [m for m in metrics if m['user_feedback'] == 'not_useful']
        partial_queries = [m for m in metrics if m['user_feedback'] == 'partial']

        # Calculate confidence statistics
        useful_confidences = [m['confidence_score'] for m in useful_queries if m['confidence_score'] is not None]
        not_useful_confidences = [m['confidence_score'] for m in not_useful_queries if m['confidence_score'] is not None]

        analysis = {
            "status": "success",
            "sample_count": len(metrics),
            "time_window_hours": time_window_hours,
            "feedback_distribution": {
                "useful": len(useful_queries),
                "not_useful": len(not_useful_queries),
                "partial": len(partial_queries)
            },
            "confidence_stats": {
                "useful_avg": statistics.mean(useful_confidences) if useful_confidences else None,
                "useful_median": statistics.median(useful_confidences) if useful_confidences else None,
                "not_useful_avg": statistics.mean(not_useful_confidences) if not_useful_confidences else None,
                "not_useful_median": statistics.median(not_useful_confidences) if not_useful_confidences else None,
            }
        }

        # Detect false positives: high confidence but not useful
        false_positives = [
            m for m in not_useful_queries
            if m['confidence_score'] and m['confidence_score'] >= 70
        ]
        analysis["false_positive_rate"] = len(false_positives) / len(metrics) if metrics else 0

        # Detect false negatives: low confidence but useful
        false_negatives = [
            m for m in useful_queries
            if m['confidence_score'] and m['confidence_score'] < 50
        ]
        analysis["false_negative_rate"] = len(false_negatives) / len(metrics) if metrics else 0

        # Calculate correlation (simplified Pearson)
        # We map: useful=1, partial=0.5, not_useful=0
        feedback_scores = []
        confidence_scores = []
        for m in metrics:
            if m['confidence_score'] is None:
                continue
            if m['user_feedback'] == 'useful':
                feedback_scores.append(1.0)
            elif m['user_feedback'] == 'partial':
                feedback_scores.append(0.5)
            else:  # not_useful
                feedback_scores.append(0.0)
            confidence_scores.append(m['confidence_score'] / 100.0)  # Normalize to 0-1

        if len(feedback_scores) >= 3:
            correlation = self._calculate_correlation(confidence_scores, feedback_scores)
            analysis["confidence_correlation"] = round(correlation, 3)
        else:
            analysis["confidence_correlation"] = None

        # Generate recommendations
        recommendations = self._generate_recommendations(analysis)
        analysis["recommendations"] = recommendations

        logger.info(f"Feedback analysis complete: {len(metrics)} samples, correlation={analysis.get('confidence_correlation')}")
        return analysis

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """
        Calculate Pearson correlation coefficient.

        Args:
            x: List of x values (confidence scores)
            y: List of y values (feedback scores)

        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        denominator_y = sum((y[i] - mean_y) ** 2 for i in range(n))

        if denominator_x == 0 or denominator_y == 0:
            return 0.0

        correlation = numerator / (denominator_x * denominator_y) ** 0.5
        return correlation

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate tuning recommendations based on analysis.

        Args:
            analysis: Analysis results dictionary

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Check correlation strength
        correlation = analysis.get("confidence_correlation")
        if correlation is not None:
            if correlation < 0.3:
                recommendations.append(
                    f"LOW CORRELATION ({correlation:.2f}): Confidence scores poorly predict usefulness. "
                    "Consider revising veracity weights or staleness thresholds."
                )
            elif correlation >= 0.7:
                recommendations.append(
                    f"STRONG CORRELATION ({correlation:.2f}): Confidence scoring is working well. "
                    "Minor tuning may still improve accuracy."
                )

        # Check false positive rate
        fp_rate = analysis.get("false_positive_rate", 0)
        if fp_rate > 0.2:  # >20% false positives
            recommendations.append(
                f"HIGH FALSE POSITIVE RATE ({fp_rate:.1%}): {fp_rate:.0%} of queries have high confidence but are not useful. "
                "Recommendation: Increase penalty for stale documents or orphaned nodes."
            )

        # Check false negative rate
        fn_rate = analysis.get("false_negative_rate", 0)
        if fn_rate > 0.2:  # >20% false negatives
            recommendations.append(
                f"HIGH FALSE NEGATIVE RATE ({fn_rate:.1%}): {fn_rate:.0%} of queries have low confidence but are useful. "
                "Recommendation: Decrease staleness penalties or increase connectivity bonus."
            )

        # Check confidence distribution mismatch
        stats = analysis.get("confidence_stats", {})
        useful_avg = stats.get("useful_avg")
        not_useful_avg = stats.get("not_useful_avg")

        if useful_avg and not_useful_avg:
            diff = useful_avg - not_useful_avg
            if diff < 10:  # Less than 10 points difference
                recommendations.append(
                    f"WEAK DISCRIMINATION: Useful queries ({useful_avg:.1f}%) vs not useful ({not_useful_avg:.1f}%) "
                    "have similar confidence scores. Increase weight adjustments to separate them better."
                )

        if not recommendations:
            recommendations.append("No major issues detected. System is performing well.")

        return recommendations

    def calculate_adjustments(
        self,
        time_window_hours: int = 24,
        project: Optional[str] = None,
        adjustment_strength: float = 0.1
    ) -> Dict[str, float]:
        """
        Calculate recommended weight adjustments based on feedback patterns.

        This uses a simple gradient-descent-like approach:
        - If false positive rate high → increase staleness penalty
        - If false negative rate high → decrease staleness penalty
        - Adjustments are capped to prevent over-correction

        Args:
            time_window_hours: Hours to analyze
            project: Filter by project (optional)
            adjustment_strength: Strength of adjustments (0.0-1.0, default: 0.1)

        Returns:
            Dictionary of weight adjustments:
                - staleness_penalty_delta: Change to staleness penalty (-5 to +5)
                - orphan_penalty_delta: Change to orphan penalty (-5 to +5)
                - connectivity_bonus_delta: Change to connectivity bonus (0 to +5)
        """
        analysis = self.analyze_feedback(time_window_hours, project, min_feedback_samples=5)

        if analysis.get("status") != "success":
            logger.warning("Insufficient data for adjustment calculation")
            return {
                "staleness_penalty_delta": 0.0,
                "orphan_penalty_delta": 0.0,
                "connectivity_bonus_delta": 0.0
            }

        adjustments = {
            "staleness_penalty_delta": 0.0,
            "orphan_penalty_delta": 0.0,
            "connectivity_bonus_delta": 0.0
        }

        fp_rate = analysis.get("false_positive_rate", 0)
        fn_rate = analysis.get("false_negative_rate", 0)

        # Adjust staleness penalty based on false positive/negative rates
        if fp_rate > 0.2:
            # Too many high-confidence but not useful → increase penalty
            adjustments["staleness_penalty_delta"] = min(5.0, fp_rate * 10 * adjustment_strength)
            logger.info(f"Recommending staleness penalty increase: +{adjustments['staleness_penalty_delta']:.1f}")

        if fn_rate > 0.2:
            # Too many low-confidence but useful → decrease penalty
            adjustments["staleness_penalty_delta"] = max(-5.0, -fn_rate * 10 * adjustment_strength)
            logger.info(f"Recommending staleness penalty decrease: {adjustments['staleness_penalty_delta']:.1f}")

        # Adjust orphan penalty similarly
        if fp_rate > 0.15:
            adjustments["orphan_penalty_delta"] = min(5.0, fp_rate * 8 * adjustment_strength)

        if fn_rate > 0.15:
            adjustments["orphan_penalty_delta"] = max(-5.0, -fn_rate * 8 * adjustment_strength)

        # Connectivity bonus: increase if false negatives are high
        if fn_rate > 0.2:
            adjustments["connectivity_bonus_delta"] = min(5.0, fn_rate * 5 * adjustment_strength)

        logger.info(f"Weight adjustments calculated: {adjustments}")
        return adjustments

    def apply_tuning(
        self,
        adjustments: Dict[str, float],
        project: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Apply tuning adjustments by storing them in Neo4j.

        Adjustments are stored as :TuningConfig nodes linked to projects.
        The ask_codebase.py veracity engine will read these to adjust scoring.

        Args:
            adjustments: Dictionary of weight adjustments
            project: Project to apply adjustments to (optional, applies globally if None)
            dry_run: If True, only simulate (don't actually store)

        Returns:
            Result dictionary with:
                - applied: bool (whether adjustments were applied)
                - dry_run: bool
                - adjustments: dict of applied adjustments
                - timestamp: when adjustments were applied
        """
        if dry_run:
            logger.info(f"DRY RUN: Would apply adjustments: {adjustments}")
            return {
                "applied": False,
                "dry_run": True,
                "adjustments": adjustments,
                "timestamp": datetime.now().isoformat()
            }

        with self.driver.session() as session:
            try:
                # Store tuning config in Neo4j
                result = session.run("""
                    MERGE (tc:TuningConfig {project: $project})
                    SET tc.staleness_penalty_delta = coalesce(tc.staleness_penalty_delta, 0.0) + $staleness_delta,
                        tc.orphan_penalty_delta = coalesce(tc.orphan_penalty_delta, 0.0) + $orphan_delta,
                        tc.connectivity_bonus_delta = coalesce(tc.connectivity_bonus_delta, 0.0) + $connectivity_delta,
                        tc.last_tuned = datetime($timestamp),
                        tc.tuning_count = coalesce(tc.tuning_count, 0) + 1

                    RETURN tc.staleness_penalty_delta as staleness_penalty_delta,
                           tc.orphan_penalty_delta as orphan_penalty_delta,
                           tc.connectivity_bonus_delta as connectivity_bonus_delta,
                           tc.tuning_count as tuning_count
                """, {
                    "project": project or "global",
                    "staleness_delta": adjustments.get("staleness_penalty_delta", 0.0),
                    "orphan_delta": adjustments.get("orphan_penalty_delta", 0.0),
                    "connectivity_delta": adjustments.get("connectivity_bonus_delta", 0.0),
                    "timestamp": datetime.now().isoformat()
                })

                record = result.single()
                if record:
                    cumulative = dict(record)
                    logger.info(f"Tuning applied: {adjustments} (cumulative: {cumulative})")
                    return {
                        "applied": True,
                        "dry_run": False,
                        "adjustments": adjustments,
                        "cumulative_adjustments": cumulative,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.error("Failed to apply tuning adjustments")
                    return {
                        "applied": False,
                        "dry_run": False,
                        "error": "Failed to store in Neo4j"
                    }

            except Exception as e:
                logger.error(f"Error applying tuning: {e}", exc_info=True)
                return {
                    "applied": False,
                    "dry_run": False,
                    "error": str(e)
                }

    def get_current_tuning(self, project: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current tuning configuration for a project.

        Args:
            project: Project name (optional, gets global if None)

        Returns:
            Dictionary with current tuning settings
        """
        with self.driver.session() as session:
            try:
                result = session.run("""
                    MATCH (tc:TuningConfig {project: $project})
                    RETURN tc.staleness_penalty_delta as staleness_penalty_delta,
                           tc.orphan_penalty_delta as orphan_penalty_delta,
                           tc.connectivity_bonus_delta as connectivity_bonus_delta,
                           tc.last_tuned as last_tuned,
                           tc.tuning_count as tuning_count
                """, {
                    "project": project or "global"
                })

                record = result.single()
                if record:
                    tuning = dict(record)
                    if tuning.get('last_tuned'):
                        tuning['last_tuned'] = str(tuning['last_tuned'])
                    return tuning
                else:
                    # No tuning applied yet - return defaults
                    return {
                        "staleness_penalty_delta": 0.0,
                        "orphan_penalty_delta": 0.0,
                        "connectivity_bonus_delta": 0.0,
                        "last_tuned": None,
                        "tuning_count": 0
                    }

            except Exception as e:
                logger.error(f"Error retrieving tuning config: {e}", exc_info=True)
                return {}

    def close(self) -> None:
        """Close connections."""
        self.metrics.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

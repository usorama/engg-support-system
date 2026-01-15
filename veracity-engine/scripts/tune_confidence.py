#!/usr/bin/env python3
"""
Confidence Tuning Cron Job.

Run daily to analyze feedback and apply ML-based confidence adjustments.

Usage:
    # Dry run (recommended first)
    python3 scripts/tune_confidence.py --dry-run

    # Apply tuning for all projects
    python3 scripts/tune_confidence.py

    # Apply tuning for specific project
    python3 scripts/tune_confidence.py --project myproject

    # Adjust tuning strength (0.0-1.0)
    python3 scripts/tune_confidence.py --strength 0.2

Schedule with cron:
    0 2 * * * cd /path/to/veracity-engine && python3 scripts/tune_confidence.py >> logs/tuning.log 2>&1
"""

import argparse
import logging
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_config, ConfigLoader
from core.metrics.confidence_tuner import ConfidenceTuner


def setup_logging(log_level: str = "INFO"):
    """Configure logging for cron job."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )


def main():
    parser = argparse.ArgumentParser(
        description="Confidence tuning cron job for Veracity Engine"
    )
    parser.add_argument(
        "--project",
        help="Project name to tune (optional, tunes globally if not specified)"
    )
    parser.add_argument(
        "--time-window",
        type=int,
        default=24,
        help="Hours of feedback to analyze (default: 24)"
    )
    parser.add_argument(
        "--strength",
        type=float,
        default=0.1,
        help="Adjustment strength 0.0-1.0 (default: 0.1)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate tuning without applying changes"
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="Minimum feedback samples required (default: 5)"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file (YAML)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results as JSON for automation"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Load configuration
    if args.config:
        ConfigLoader.load(config_file=args.config)
    else:
        ConfigLoader.load()

    logger.info("="*80)
    logger.info(f"Confidence Tuning Job Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Project: {args.project or 'global'}")
    logger.info(f"Time Window: {args.time_window} hours")
    logger.info(f"Adjustment Strength: {args.strength}")
    logger.info(f"Dry Run: {args.dry_run}")
    logger.info("="*80)

    results = {
        "timestamp": datetime.now().isoformat(),
        "project": args.project or "global",
        "time_window_hours": args.time_window,
        "dry_run": args.dry_run,
        "success": False
    }

    try:
        with ConfidenceTuner() as tuner:
            # Step 1: Analyze feedback
            logger.info("\n[1/3] Analyzing feedback patterns...")
            analysis = tuner.analyze_feedback(
                time_window_hours=args.time_window,
                project=args.project,
                min_feedback_samples=args.min_samples
            )

            results["analysis"] = analysis

            if analysis.get("status") != "success":
                logger.warning(f"Analysis status: {analysis.get('status')}")
                logger.warning(f"Reason: {analysis.get('recommendations', ['Unknown'])[0]}")
                results["success"] = False
                results["message"] = "Insufficient data for tuning"
                if args.json_output:
                    print(json.dumps(results, indent=2))
                return 0

            # Log analysis results
            logger.info(f"  Sample count: {analysis['sample_count']}")
            logger.info(f"  Feedback distribution: {analysis['feedback_distribution']}")
            logger.info(f"  Confidence correlation: {analysis.get('confidence_correlation', 'N/A')}")
            logger.info(f"  False positive rate: {analysis.get('false_positive_rate', 0):.1%}")
            logger.info(f"  False negative rate: {analysis.get('false_negative_rate', 0):.1%}")

            logger.info("\n  Recommendations:")
            for rec in analysis.get("recommendations", []):
                logger.info(f"    - {rec}")

            # Step 2: Calculate adjustments
            logger.info("\n[2/3] Calculating weight adjustments...")
            adjustments = tuner.calculate_adjustments(
                time_window_hours=args.time_window,
                project=args.project,
                adjustment_strength=args.strength
            )

            results["adjustments"] = adjustments

            logger.info(f"  Staleness penalty delta: {adjustments['staleness_penalty_delta']:+.2f}")
            logger.info(f"  Orphan penalty delta: {adjustments['orphan_penalty_delta']:+.2f}")
            logger.info(f"  Connectivity bonus delta: {adjustments['connectivity_bonus_delta']:+.2f}")

            # Check if any adjustments are non-zero
            has_adjustments = any(abs(v) > 0.01 for v in adjustments.values())

            if not has_adjustments:
                logger.info("\n  No significant adjustments needed - system is well-calibrated")
                results["success"] = True
                results["message"] = "No adjustments needed"
                if args.json_output:
                    print(json.dumps(results, indent=2))
                return 0

            # Step 3: Apply tuning
            logger.info(f"\n[3/3] Applying tuning (dry_run={args.dry_run})...")
            apply_result = tuner.apply_tuning(
                adjustments=adjustments,
                project=args.project,
                dry_run=args.dry_run
            )

            results["apply_result"] = apply_result

            if apply_result.get("applied"):
                logger.info("  ✓ Tuning applied successfully")
                cumulative = apply_result.get("cumulative_adjustments", {})
                logger.info(f"  Cumulative adjustments:")
                logger.info(f"    Staleness penalty: {cumulative.get('staleness_penalty_delta', 0):+.2f}")
                logger.info(f"    Orphan penalty: {cumulative.get('orphan_penalty_delta', 0):+.2f}")
                logger.info(f"    Connectivity bonus: {cumulative.get('connectivity_bonus_delta', 0):+.2f}")
                logger.info(f"    Total tunings applied: {cumulative.get('tuning_count', 0)}")
                results["success"] = True
                results["message"] = "Tuning applied successfully"
            elif args.dry_run:
                logger.info("  DRY RUN: Adjustments simulated (not applied)")
                results["success"] = True
                results["message"] = "Dry run completed"
            else:
                logger.error("  ✗ Failed to apply tuning")
                logger.error(f"    Error: {apply_result.get('error', 'Unknown')}")
                results["success"] = False
                results["message"] = f"Failed to apply: {apply_result.get('error', 'Unknown')}"

            # Get current tuning state
            current = tuner.get_current_tuning(project=args.project)
            results["current_tuning"] = current

    except Exception as e:
        logger.error(f"Tuning job failed: {e}", exc_info=True)
        results["success"] = False
        results["message"] = f"Exception: {str(e)}"
        if args.json_output:
            print(json.dumps(results, indent=2))
        return 1

    finally:
        logger.info("="*80)
        logger.info(f"Confidence Tuning Job Completed - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)

    # Output JSON if requested
    if args.json_output:
        print(json.dumps(results, indent=2))

    return 0 if results["success"] else 1


if __name__ == "__main__":
    sys.exit(main())

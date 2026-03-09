"""Learning loop — periodic job that updates ML weights from outcomes.

Designed to run daily (or on-demand) to:
1. Fetch recent outcomes with resolution
2. Run anomaly_tuner.compute_weight_adjustments()
3. Run confidence_tuner.evaluate_thresholds()
4. Run provider_tracker.compute_scorecards()
5. Log tuning report for observability
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run_learning_loop(
    *,
    outcome_tracker: Any | None = None,
    anomaly_engine: Any | None = None,
    confidence_router: Any | None = None,
    provider_tracker: Any | None = None,
) -> dict[str, Any]:
    """Execute one cycle of the learning loop.

    Returns:
        Summary dict with tuning reports
    """
    results: dict[str, Any] = {"status": "completed", "steps": {}}

    # Step 1: Gather resolved outcomes
    resolved_outcomes = []
    if outcome_tracker is not None:
        try:
            all_outcomes = list(outcome_tracker._outcomes.values())
            resolved_outcomes = [o for o in all_outcomes if o.resolved_at is not None]
            results["steps"]["outcomes_gathered"] = len(resolved_outcomes)
        except Exception as e:
            logger.error("Learning loop: failed to gather outcomes: %s", e)
            results["steps"]["outcomes_gathered"] = f"error: {e}"

    # Step 2: Anomaly tuner
    if anomaly_engine is not None and resolved_outcomes:
        try:
            from sardis_guardrails.anomaly_tuner import AnomalyTuner

            tuner = AnomalyTuner()
            new_weights = await tuner.compute_weight_adjustments(
                resolved_outcomes, dict(anomaly_engine.WEIGHTS),
            )
            await tuner.apply_adjustments(anomaly_engine, new_weights)
            report = await tuner.get_tuning_report()
            results["steps"]["anomaly_tuning"] = report.to_dict() if report else "no_report"
        except Exception as e:
            logger.error("Learning loop: anomaly tuning failed: %s", e)
            results["steps"]["anomaly_tuning"] = f"error: {e}"

    # Step 3: Confidence tuner
    if confidence_router is not None and resolved_outcomes:
        try:
            from sardis_v2_core.confidence_tuner import ConfidenceTuner

            tuner = ConfidenceTuner()
            recommendation = await tuner.evaluate_thresholds(
                resolved_outcomes, confidence_router.thresholds,
            )
            results["steps"]["confidence_tuning"] = recommendation.to_dict()
        except Exception as e:
            logger.error("Learning loop: confidence tuning failed: %s", e)
            results["steps"]["confidence_tuning"] = f"error: {e}"

    # Step 4: Provider scorecards
    if provider_tracker is not None:
        try:
            await provider_tracker.compute_scorecards()
            scorecards = await provider_tracker.get_all_scorecards()
            results["steps"]["provider_scorecards"] = len(scorecards)
        except Exception as e:
            logger.error("Learning loop: provider scorecard computation failed: %s", e)
            results["steps"]["provider_scorecards"] = f"error: {e}"

    logger.info("Learning loop completed: %s", results)
    return results

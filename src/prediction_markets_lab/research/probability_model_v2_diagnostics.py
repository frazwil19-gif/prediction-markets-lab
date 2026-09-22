"""Phase 2 (probability-model research) diagnostic helpers.

Pure, side-effect-free functions used to slice already-computed,
out-of-sample match predictions into the two granular views the
"PHASE 2 -- INDEPENDENT FOOTBALL PROBABILITY MODEL RESEARCH" instruction
asked for beyond what Gate 1 (research/cycles/CYCLE_003_FOOTBALL/
GATE1_CHECKPOINT.md, 2026-09-18) already produced:

1. High-probability-region reliability (instruction Section 13): for
   predictions >=50%, bucketed into 50-54.9% / 55-59.9% / 60-64.9% /
   65-69.9% / 70-79.9% / 80%+, report count, mean predicted probability,
   actual win rate, calibration error, and the market's own probability
   for the same (match, outcome) for comparison.

2. Disagreement-band analysis (instruction Section 15): bucket
   (candidate_model_probability - market_probability) into bands and
   check, prospectively/chronologically (the input rows are assumed to
   already be out-of-sample), whether the direction and size of
   disagreement is itself informative about the realised outcome.

These functions take already-computed predictions (from a chronological
walk-forward or holdout evaluation) as plain dicts/floats -- they do not
fit any model and do not touch raw match data, so there is no leakage
risk to audit here beyond "were the input predictions themselves
computed out-of-sample," which is the caller's responsibility (see
scripts/run_probability_model_v2_diagnostics.py, which reuses Gate 1's
already-audited walk-forward procedure to produce them).
"""

from __future__ import annotations

from dataclasses import dataclass

HIGH_PROBABILITY_BANDS: tuple[tuple[str, float, float], ...] = (
    ("50-54.9%", 0.50, 0.549999999),
    ("55-59.9%", 0.55, 0.599999999),
    ("60-64.9%", 0.60, 0.649999999),
    ("65-69.9%", 0.65, 0.699999999),
    ("70-79.9%", 0.70, 0.799999999),
    ("80%+", 0.80, 1.000000001),
)

DISAGREEMENT_BANDS: tuple[tuple[str, float, float], ...] = (
    ("model << market (<= -0.20)", -1.000001, -0.20),
    ("model < market (-0.20, -0.10]", -0.20, -0.10),
    ("model < market (-0.10, -0.05]", -0.10, -0.05),
    ("model ~= market (-0.05, +0.05)", -0.05, 0.05),
    ("model > market [+0.05, +0.10)", 0.05, 0.10),
    ("model > market [+0.10, +0.20)", 0.10, 0.20),
    ("model >> market (>= +0.20)", 0.20, 1.000001),
)


def band_for_probability(probability: float) -> str | None:
    """Return the HIGH_PROBABILITY_BANDS label containing `probability`,
    or None if it is below 50% (out of scope for this analysis)."""
    for label, lower, upper in HIGH_PROBABILITY_BANDS:
        if lower <= probability <= upper:
            return label
    return None


def band_for_disagreement(model_minus_market: float) -> str:
    """Return the DISAGREEMENT_BANDS label containing the signed
    difference (model_probability - market_probability). Always returns
    a label -- the bands are exhaustive over [-1, 1]."""
    for label, lower, upper in DISAGREEMENT_BANDS:
        if lower <= model_minus_market < upper or (label == DISAGREEMENT_BANDS[-1][0] and model_minus_market >= lower):
            return label
    # Exact +1.0 edge case or floating point at the extreme.
    return DISAGREEMENT_BANDS[-1][0]


@dataclass(frozen=True)
class HighProbabilityBandResult:
    band: str
    n: int
    mean_predicted_probability: float | None
    actual_win_rate: float | None
    calibration_error: float | None
    mean_market_probability: float | None
    mean_difference_from_market: float | None


def high_probability_region_report(
    predicted_probabilities: list[float],
    market_probabilities: list[float],
    actual_outcomes: list[bool],
) -> list[HighProbabilityBandResult]:
    """Bucket (predicted_probability, market_probability, actual_outcome)
    triples -- one per candidate (match, outcome) already restricted to
    a single model's out-of-sample predictions -- into
    HIGH_PROBABILITY_BANDS and report per-band reliability.

    Only candidates with predicted_probability >= 50% are considered
    (matching instruction Section 13's explicit scope, since this is
    the region the money-qualification gate actually cares about).
    Bands with zero matching candidates are still returned (n=0, all
    other fields None) so an empty bucket is visible rather than
    silently missing -- never claim a rate from an empty bin.
    """
    if not (len(predicted_probabilities) == len(market_probabilities) == len(actual_outcomes)):
        raise ValueError("predicted_probabilities, market_probabilities, and actual_outcomes must be the same length")

    buckets: dict[str, list[tuple[float, float, bool]]] = {label: [] for label, _, _ in HIGH_PROBABILITY_BANDS}
    for pred, mkt, actual in zip(predicted_probabilities, market_probabilities, actual_outcomes):
        label = band_for_probability(pred)
        if label is not None:
            buckets[label].append((pred, mkt, actual))

    results = []
    for label, _, _ in HIGH_PROBABILITY_BANDS:
        rows = buckets[label]
        if not rows:
            results.append(HighProbabilityBandResult(label, 0, None, None, None, None, None))
            continue
        preds = [r[0] for r in rows]
        mkts = [r[1] for r in rows]
        actuals = [1.0 if r[2] else 0.0 for r in rows]
        mean_pred = sum(preds) / len(preds)
        win_rate = sum(actuals) / len(actuals)
        mean_mkt = sum(mkts) / len(mkts)
        results.append(HighProbabilityBandResult(
            band=label,
            n=len(rows),
            mean_predicted_probability=mean_pred,
            actual_win_rate=win_rate,
            calibration_error=abs(mean_pred - win_rate),
            mean_market_probability=mean_mkt,
            mean_difference_from_market=mean_pred - mean_mkt,
        ))
    return results


@dataclass(frozen=True)
class DisagreementBandResult:
    band: str
    n: int
    mean_model_probability: float | None
    mean_market_probability: float | None
    actual_win_rate: float | None
    model_calibration_error: float | None
    market_calibration_error: float | None


def disagreement_band_report(
    model_probabilities: list[float],
    market_probabilities: list[float],
    actual_outcomes: list[bool],
) -> list[DisagreementBandResult]:
    """Bucket candidates by signed (model - market) probability
    difference and report, within each band, whether the model or the
    market was closer to the realised outcome frequency.

    This answers instruction Section 15's actual question -- not "did
    individual disagreeing bets win" but "is disagreement of this size
    and direction systematically associated with the model or the
    market being closer to right, out-of-sample." All bands are
    returned even when empty, so a missing bucket cannot be silently
    dropped from the report.
    """
    if not (len(model_probabilities) == len(market_probabilities) == len(actual_outcomes)):
        raise ValueError("model_probabilities, market_probabilities, and actual_outcomes must be the same length")

    buckets: dict[str, list[tuple[float, float, bool]]] = {label: [] for label, _, _ in DISAGREEMENT_BANDS}
    for model_p, mkt_p, actual in zip(model_probabilities, market_probabilities, actual_outcomes):
        label = band_for_disagreement(model_p - mkt_p)
        buckets[label].append((model_p, mkt_p, actual))

    results = []
    for label, _, _ in DISAGREEMENT_BANDS:
        rows = buckets[label]
        if not rows:
            results.append(DisagreementBandResult(label, 0, None, None, None, None, None))
            continue
        model_ps = [r[0] for r in rows]
        mkt_ps = [r[1] for r in rows]
        actuals = [1.0 if r[2] else 0.0 for r in rows]
        mean_model = sum(model_ps) / len(model_ps)
        mean_mkt = sum(mkt_ps) / len(mkt_ps)
        win_rate = sum(actuals) / len(actuals)
        results.append(DisagreementBandResult(
            band=label,
            n=len(rows),
            mean_model_probability=mean_model,
            mean_market_probability=mean_mkt,
            actual_win_rate=win_rate,
            model_calibration_error=abs(mean_model - win_rate),
            market_calibration_error=abs(mean_mkt - win_rate),
        ))
    return results

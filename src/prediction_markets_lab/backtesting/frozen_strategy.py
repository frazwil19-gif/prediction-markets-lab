"""Freeze the current production money-qualification strategy before any
historical backtest run.

"Freeze the current production V1 strategy/configuration -- a versioned,
hashed snapshot ... never silently updated by future config changes."
This module does not invent a parallel config schema -- it loads
config/thresholds.yaml and config/bankroll.yaml through the EXACT SAME
builder functions scripts/run_daily_scan.py already uses (imported
directly, not re-implemented), so a frozen strategy is provably "what
production actually runs," not a hand-copied approximation of it.

The frozen strategy is identified by a name (STRATEGY_NAME) plus a
content hash of every threshold value it captured -- if config/*.yaml
ever changes, the hash changes, and a backtest run recorded against the
old hash is visibly tied to the configuration that was actually frozen,
never silently re-interpreted against new thresholds.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# scripts/ is not a package (no __init__.py) -- run_daily_scan.py is
# imported this way so the SAME builder functions are reused rather than
# re-implemented, per the module docstring.
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_daily_scan as _run_daily_scan  # noqa: E402  (see sys.path note above)

STRATEGY_NAME = "money-strategy-v1-frozen"

# The engine version this freeze corresponds to. Mirrors
# reports.daily_bet_card.ENGINE_VERSION at the time this package was
# built -- if that version string changes in a future production release,
# a NEW freeze must be taken (this constant is not auto-derived from the
# live ENGINE_VERSION on purpose: a frozen strategy must stay exactly what
# it said it was, not silently track a future engine version).
FROZEN_ENGINE_VERSION_AT_FREEZE_TIME = "daily-engine-v1"


@dataclass(frozen=True)
class FrozenStrategy:
    """A versioned, hashed snapshot of the production money-qualification
    strategy, suitable for recording alongside every backtest run."""

    strategy_name: str
    frozen_at_engine_version: str
    thresholds: dict
    bankroll: dict
    config_hash: str


def _canonical_json(payload: dict) -> str:
    """Stable, whitespace-fixed JSON serialisation used for hashing.

    sort_keys=True + fixed separators ensure the same logical config
    always hashes identically regardless of dict insertion order.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def load_and_freeze_current_strategy() -> FrozenStrategy:
    """Load config/thresholds.yaml and config/bankroll.yaml via the exact
    production builder functions, and freeze the result.

    Returns:
        A FrozenStrategy capturing every threshold dataclass the
        production recommendation pipeline uses, plus a content hash
        proving what was captured.

    Raises:
        Whatever run_daily_scan.load_yaml/build_*_thresholds raise if
        config/*.yaml is missing a required key -- this module never
        supplies its own defaults for a value production requires.
    """
    thresholds_yaml = _run_daily_scan.load_yaml(REPO_ROOT / "config" / "thresholds.yaml")
    bankroll_yaml = _run_daily_scan.load_yaml(REPO_ROOT / "config" / "bankroll.yaml")

    grading = _run_daily_scan.build_grading_thresholds(thresholds_yaml)
    confidence = _run_daily_scan.build_confidence_thresholds(thresholds_yaml)
    data_quality = _run_daily_scan.build_data_quality_thresholds(thresholds_yaml)
    payout_policy = _run_daily_scan.build_payout_policy_thresholds(thresholds_yaml)
    money_qualification = _run_daily_scan.build_money_qualification_thresholds(thresholds_yaml)
    staking = _run_daily_scan.build_staking_config()

    # dataclasses.asdict on a frozenset field would leave a non-JSON-
    # serialisable frozenset in the dict -- convert those two fields to
    # sorted lists explicitly so the payload is both JSON-safe and
    # order-independent for hashing.
    money_qualification_dict = asdict(money_qualification)
    money_qualification_dict["eligible_confidence_labels"] = sorted(
        money_qualification.eligible_confidence_labels
    )
    money_qualification_dict["conditional_confidence_labels"] = sorted(
        money_qualification.conditional_confidence_labels
    )

    thresholds_payload = {
        "grading": asdict(grading),
        "confidence": asdict(confidence),
        "data_quality": asdict(data_quality),
        "payout_policy": asdict(payout_policy),
        "money_qualification": money_qualification_dict,
    }
    bankroll_payload = asdict(staking)

    full_payload = {
        "strategy_name": STRATEGY_NAME,
        "frozen_at_engine_version": FROZEN_ENGINE_VERSION_AT_FREEZE_TIME,
        "thresholds": thresholds_payload,
        "bankroll": bankroll_payload,
    }
    config_hash = hashlib.sha256(_canonical_json(full_payload).encode("utf-8")).hexdigest()

    return FrozenStrategy(
        strategy_name=STRATEGY_NAME,
        frozen_at_engine_version=FROZEN_ENGINE_VERSION_AT_FREEZE_TIME,
        thresholds=thresholds_payload,
        bankroll=bankroll_payload,
        config_hash=config_hash,
    )


def frozen_strategy_to_dict(strategy: FrozenStrategy) -> dict:
    """JSON-safe dict form of a FrozenStrategy, for manifest.json."""
    return {
        "strategy_name": strategy.strategy_name,
        "frozen_at_engine_version": strategy.frozen_at_engine_version,
        "thresholds": strategy.thresholds,
        "bankroll": strategy.bankroll,
        "config_hash": strategy.config_hash,
    }


def rebuild_threshold_objects(strategy: FrozenStrategy) -> dict:
    """Reconstruct the actual production threshold dataclasses from a
    frozen strategy's captured values, for use by the replay harness.

    This is how a backtest run stays pinned to the EXACT thresholds it
    was frozen with, even if config/thresholds.yaml is edited afterwards
    for live production -- the replay harness must call this rather than
    re-reading config/*.yaml directly.

    Returns:
        A dict with keys "grading", "confidence", "data_quality",
        "payout_policy", "money_qualification", "staking", each holding
        the corresponding rebuilt dataclass instance.
    """
    from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
    from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
    from prediction_markets_lab.decisions.grading import GradingThresholds
    from prediction_markets_lab.decisions.money_qualification import MoneyQualificationThresholds
    from prediction_markets_lab.decisions.payout_policy import PayoutPolicyThresholds
    from prediction_markets_lab.risk.staking import StakingConfig

    t = strategy.thresholds
    mq = dict(t["money_qualification"])
    mq["eligible_confidence_labels"] = frozenset(mq["eligible_confidence_labels"])
    mq["conditional_confidence_labels"] = frozenset(mq["conditional_confidence_labels"])

    return {
        "grading": GradingThresholds(**t["grading"]),
        "confidence": ConfidenceThresholds(**t["confidence"]),
        "data_quality": DataQualityThresholds(**t["data_quality"]),
        "payout_policy": PayoutPolicyThresholds(**t["payout_policy"]),
        "money_qualification": MoneyQualificationThresholds(**mq),
        "staking": StakingConfig(**strategy.bankroll),
    }

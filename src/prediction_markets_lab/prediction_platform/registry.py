"""Engine registry access: research/platform_v2/PROBABILITY_ENGINE_REGISTRY.json is the single source of truth."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "research/platform_v2/PROBABILITY_ENGINE_REGISTRY.json"
REQUIRED = ("engine_id", "sport", "market", "ledger_version", "status", "probability_source", "historical_sample",
            "sealed_holdout_status", "prospective_status", "settlement_source", "ge80_historical_coverage",
            "historical_calibration", "money_eligible", "multi_research_eligible", "collect", "last_updated")
MONEY_OK_STATUSES = ("VALIDATED_HISTORICAL", "VALIDATED_HISTORICAL_AND_PROSPECTIVE")


class Registry:
    def __init__(self, data: dict):
        self.data = data
        self.engines = {e["engine_id"]: e for e in data["engines"]}

    @classmethod
    def load(cls, path: Path = REGISTRY_PATH) -> "Registry":
        return cls(json.loads(path.read_text()))

    def get(self, engine_id: str) -> dict:
        if engine_id not in self.engines:
            raise KeyError(f"ENGINE_UNKNOWN: {engine_id}")
        return self.engines[engine_id]

    def validate(self) -> list[str]:
        errs = []
        vocab, pvocab = set(self.data["status_vocabulary"]), set(self.data["prospective_vocabulary"])
        for eid, e in self.engines.items():
            errs += [f"{eid}: missing {k}" for k in REQUIRED if k not in e]
            if e.get("status") not in vocab:
                errs.append(f"{eid}: bad status {e.get('status')}")
            if e.get("prospective_status") not in pvocab:
                errs.append(f"{eid}: bad prospective_status {e.get('prospective_status')}")
            if e.get("money_eligible") and e.get("status") not in MONEY_OK_STATUSES:
                errs.append(f"{eid}: money_eligible with status {e.get('status')}")
            if e.get("prospective_status") == "AWAITING_SEASON" and not e.get("activation_date_utc"):
                errs.append(f"{eid}: AWAITING_SEASON without activation_date_utc")
        return errs

    def collectable(self, engine_id: str, now: datetime) -> bool:
        e = self.get(engine_id)
        if not e.get("collect") or e.get("status") in ("BLOCKED", "RETIRED"):
            return False
        if e["prospective_status"] == "COLLECTING":
            return True
        if e["prospective_status"] == "AWAITING_SEASON":
            return now.date().isoformat() >= e["activation_date_utc"]
        return False

    def support_text(self, engine_id: str) -> str:
        e = self.get(engine_id)
        return (f"hist n={e['historical_sample']}; holdout {e['sealed_holdout_status']}; "
                f">=80% coverage {e['ge80_historical_coverage']}; {e['historical_calibration']}")

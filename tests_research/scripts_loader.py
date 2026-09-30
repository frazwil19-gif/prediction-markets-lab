"""Load scripts/run_card_shadow.py as a module for tests (scripts/ is not a package)."""
import importlib.util
import sys
from pathlib import Path


def load_cli():
    p = Path(__file__).resolve().parents[1] / "scripts/run_card_shadow.py"
    spec = importlib.util.spec_from_file_location("run_card_shadow_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

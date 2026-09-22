"""Historical backtesting of frozen production money-qualification strategies.

BACKTEST PHASE 1 (2026-09-22): "audit + build the honest replay framework
+ run the first frozen-V1 backtest only where the data supports it." This
package never duplicates decision logic already tested in
decisions/recommendation.py and its dependents -- it freezes the exact
config those modules already load (frozen_strategy.py), replays real
historical data through the exact same call (replay.py), and reports the
result with the project's existing performance metrics modules
(metrics.py, report.py). See research/backtesting/ for the feasibility
and leakage audits this package's design is answerable to.
"""

from __future__ import annotations

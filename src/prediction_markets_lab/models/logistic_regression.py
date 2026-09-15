"""A small, from-scratch multi-feature logistic regression via
Newton-Raphson / IRLS -- no sklearn/scipy dependency in this project's
environment (see prediction_markets_lab.performance.binary_classification
for the same reasoning applied to its 2-parameter calibration fit, which
is a special case of this).

Deliberately minimal: this is a handful of numeric features and a
closed-form Newton step, not a general-purpose ML library. Built for
Workstream A4's tennis baselines (research/cycles/CYCLE_002_TENNIS/), where
the whole point is "robust baselines, not a Kaggle competition" -- no
regularisation path, no feature scaling pipeline, no solver options.
Optional L2 ridge regularisation is included ONLY because an unregularised
fit can fail to converge or blow up when a feature is a near-perfect
separator (a real risk with a strong feature like an Elo rating
difference) -- it defaults to a small fixed value, not something to be
tuned per model.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_EPS = 1e-15
DEFAULT_L2_PENALTY = 1e-6


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -35, 35)))


@dataclass(frozen=True)
class FittedLogisticModel:
    feature_names: tuple[str, ...]
    intercept: float
    coefficients: tuple[float, ...]
    n_train: int
    n_iterations: int

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """features: shape (n, len(feature_names)), same column order as
        feature_names. Returns P(outcome==1) for each row."""
        features = np.asarray(features, dtype=float)
        if features.ndim == 1:
            features = features.reshape(1, -1)
        if features.shape[1] != len(self.feature_names):
            raise ValueError(
                f"expected {len(self.feature_names)} features "
                f"({self.feature_names}), got {features.shape[1]}"
            )
        eta = self.intercept + features @ np.array(self.coefficients)
        return _sigmoid(eta)


def fit_logistic_regression(
    features: np.ndarray,
    outcomes: list[int],
    feature_names: list[str],
    l2_penalty: float = DEFAULT_L2_PENALTY,
    max_iter: int = 100,
    tol: float = 1e-8,
) -> FittedLogisticModel:
    """Fit intercept + coefficients via IRLS with a small ridge penalty on
    the coefficients only (never on the intercept -- standard convention).

    Args:
        features: shape (n, k) numeric feature matrix, already fully
            resolved (no NaNs -- the caller is responsible for dropping
            or imputing missing rows before fitting; this function does
            not silently do either).
        outcomes: length-n list of 0/1 outcomes.
        feature_names: length-k names, used only for FittedLogisticModel's
            bookkeeping and error messages.
        l2_penalty: ridge coefficient (see module docstring for why this
            has a small non-zero default rather than 0.0).

    Returns:
        A FittedLogisticModel.

    Raises:
        ValueError: on shape mismatches, empty input, or non-convergence
            within max_iter.
    """
    features = np.asarray(features, dtype=float)
    if features.ndim == 1:
        features = features.reshape(-1, 1)
    n, k = features.shape
    if len(outcomes) != n:
        raise ValueError(f"features has {n} rows but outcomes has {len(outcomes)} entries")
    if len(feature_names) != k:
        raise ValueError(f"features has {k} columns but {len(feature_names)} feature_names given")
    if n == 0:
        raise ValueError("cannot fit logistic regression on zero rows")
    if np.isnan(features).any():
        raise ValueError("features contains NaN -- resolve missing values before fitting")

    y = np.asarray(outcomes, dtype=float)
    design = np.column_stack([np.ones(n), features])  # [intercept, feature_1, ..., feature_k]
    beta = np.zeros(k + 1)
    penalty_matrix = l2_penalty * np.eye(k + 1)
    penalty_matrix[0, 0] = 0.0  # never penalise the intercept

    n_iterations = 0
    for i in range(max_iter):
        n_iterations = i + 1
        eta = design @ beta
        mu = _sigmoid(eta)
        w = np.clip(mu * (1.0 - mu), 1e-10, None)
        gradient = design.T @ (y - mu) - penalty_matrix @ beta
        hessian = -(design.T * w) @ design - penalty_matrix
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError as exc:
            raise ValueError("IRLS Hessian is singular -- logistic fit failed to converge") from exc
        beta = beta - step
        if np.max(np.abs(step)) < tol:
            break
    else:
        raise ValueError(f"logistic regression did not converge within {max_iter} iterations")

    return FittedLogisticModel(
        feature_names=tuple(feature_names),
        intercept=float(beta[0]),
        coefficients=tuple(beta[1:].tolist()),
        n_train=n,
        n_iterations=n_iterations,
    )

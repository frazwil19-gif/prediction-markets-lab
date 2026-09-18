"""A small, from-scratch multinomial (softmax) logistic regression for
3-outcome (home/draw/away) match probability estimation -- no
sklearn/scipy dependency in this project's environment, exactly the same
reasoning as models/logistic_regression.py (binary IRLS) and
performance/binary_classification.py's 2-parameter calibration fit.

Built for Gate 1 of the Daily Probability Engine's football probability-
architecture experiment (research/cycles/CYCLE_003_FOOTBALL/
GATE1_PROBABILITY_ARCHITECTURE_PROTOCOL.md): "MODEL 2" (fundamentals-only)
and "MODEL 3" (market + fundamentals) both need a genuine multi-feature,
multi-class classifier, which the existing binary IRLS module cannot
provide (home/draw/away is 3 classes, not 2).

Deliberately minimal, matching this project's stated preference for
transparent models before complex ones: full-parameterisation softmax
regression (one weight vector per class, not a baseline-class
reduction), trained by full-batch gradient descent with Adam-style
adaptive per-parameter learning rates (a standard, well-documented
optimiser -- not a novel algorithm) rather than a hand-rolled
multinomial Newton-Raphson, whose block Hessian is materially more
complex to implement correctly than the binary case. L2 ridge
regularisation on the class weight vectors (never on the intercepts) is
required, not optional, here: softmax is invariant to adding a constant
vector to every class's logits, so an unregularised full-parameterisation
fit is not identifiable; a small ridge penalty on every class's weights
breaks that redundancy and yields a unique, stable solution. Feature
standardisation (z-score, fit on training data only) is handled inside
this module rather than left to the caller, because gradient descent's
convergence speed is sensitive to feature scale in a way Newton-Raphson
(used by the binary IRLS module) is not.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_L2_PENALTY = 1e-3
DEFAULT_LEARNING_RATE = 0.15
DEFAULT_MAX_ITER = 4000
DEFAULT_TOL = 1e-7


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Row-wise softmax, numerically stabilised by subtracting the row max."""
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


@dataclass(frozen=True)
class FittedMultinomialModel:
    feature_names: tuple[str, ...]
    classes: tuple[str, ...]
    intercepts: tuple[float, ...]  # one per class, same order as `classes`
    coefficients: tuple[tuple[float, ...], ...]  # coefficients[k] = this class's weight vector, standardised-feature space
    feature_means: tuple[float, ...]  # training-only, used to standardise new data identically
    feature_stds: tuple[float, ...]  # training-only; a zero-variance feature is stored as std=1.0 (no-op transform)
    n_train: int
    n_iterations: int
    final_max_gradient_norm: float

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """features: shape (n, len(feature_names)), same column order and
        RAW (unstandardised) scale as at fit time. Returns shape
        (n, len(classes)) probabilities, one row per input row, summing
        to 1.0 per row."""
        features = np.asarray(features, dtype=float)
        if features.ndim == 1:
            features = features.reshape(1, -1)
        if features.shape[1] != len(self.feature_names):
            raise ValueError(
                f"expected {len(self.feature_names)} features ({self.feature_names}), "
                f"got {features.shape[1]}"
            )
        means = np.array(self.feature_means)
        stds = np.array(self.feature_stds)
        standardised = (features - means) / stds
        weights = np.array(self.coefficients)  # (K, p)
        intercepts = np.array(self.intercepts)  # (K,)
        logits = standardised @ weights.T + intercepts  # (n, K)
        return _softmax(logits)

    def predict_proba_dict(self, features: np.ndarray) -> list[dict[str, float]]:
        """Convenience wrapper returning one {class_name: probability} dict per row."""
        probs = self.predict_proba(features)
        return [dict(zip(self.classes, row.tolist())) for row in probs]


def fit_multinomial_logistic_regression(
    features: np.ndarray,
    outcomes: list[str],
    feature_names: list[str],
    classes: tuple[str, ...],
    l2_penalty: float = DEFAULT_L2_PENALTY,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    max_iter: int = DEFAULT_MAX_ITER,
    tol: float = DEFAULT_TOL,
    seed: int = 0,
) -> FittedMultinomialModel:
    """Fit a full-parameterisation softmax regression via full-batch Adam.

    Args:
        features: shape (n, k) numeric feature matrix, already fully
            resolved (no NaNs -- the caller is responsible for dropping
            or imputing missing rows before fitting; this function does
            not silently do either, matching models/logistic_regression.py).
        outcomes: length-n list of class labels, each one of `classes`.
        feature_names: length-k names, used only for bookkeeping/error messages.
        classes: the fixed, ordered set of class labels (e.g.
            ("home", "draw", "away")) -- fixed here rather than inferred
            from `outcomes` so a fold whose training data happens to
            contain zero examples of one class still produces a model
            that can predict all three.
        l2_penalty: ridge coefficient on every class's weight vector
            (never the intercepts) -- see module docstring for why this
            must be > 0, not merely a tunable default.
        learning_rate, max_iter, tol, seed: Adam optimiser controls.
            seed controls only the all-zero-with-tiny-jitter parameter
            initialisation (kept for exact reproducibility across runs,
            not because the loss surface is expected to have troublesome
            local minima at this model's scale).

    Returns:
        A FittedMultinomialModel.

    Raises:
        ValueError: on shape mismatches, empty input, non-positive
            l2_penalty, an outcome value not in `classes`, or NaN features.
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
        raise ValueError("cannot fit multinomial logistic regression on zero rows")
    if np.isnan(features).any():
        raise ValueError("features contains NaN -- resolve missing values before fitting")
    if l2_penalty <= 0:
        raise ValueError(f"l2_penalty must be > 0 (required for identifiability), got {l2_penalty}")
    bad_outcomes = set(outcomes) - set(classes)
    if bad_outcomes:
        raise ValueError(f"outcomes contains values not in classes={classes}: {bad_outcomes}")

    means = features.mean(axis=0)
    stds = features.std(axis=0)
    stds_safe = np.where(stds > 1e-12, stds, 1.0)
    standardised = (features - means) / stds_safe

    n_classes = len(classes)
    class_index = {c: i for i, c in enumerate(classes)}
    y_onehot = np.zeros((n, n_classes))
    for i, outcome in enumerate(outcomes):
        y_onehot[i, class_index[outcome]] = 1.0

    rng = np.random.default_rng(seed)
    weights = rng.normal(scale=1e-3, size=(n_classes, k))
    intercepts = np.zeros(n_classes)

    # Adam state.
    m_w, v_w = np.zeros_like(weights), np.zeros_like(weights)
    m_b, v_b = np.zeros_like(intercepts), np.zeros_like(intercepts)
    beta1, beta2, adam_eps = 0.9, 0.999, 1e-8

    design = standardised  # (n, k)
    n_iterations = 0
    final_grad_norm = float("inf")
    for t in range(1, max_iter + 1):
        n_iterations = t
        logits = design @ weights.T + intercepts  # (n, K)
        probs = _softmax(logits)
        residual = probs - y_onehot  # (n, K)

        grad_w = (residual.T @ design) / n + l2_penalty * weights  # (K, k)
        grad_b = residual.mean(axis=0)  # (K,)

        m_w = beta1 * m_w + (1 - beta1) * grad_w
        v_w = beta2 * v_w + (1 - beta2) * (grad_w**2)
        m_b = beta1 * m_b + (1 - beta1) * grad_b
        v_b = beta2 * v_b + (1 - beta2) * (grad_b**2)

        m_w_hat = m_w / (1 - beta1**t)
        v_w_hat = v_w / (1 - beta2**t)
        m_b_hat = m_b / (1 - beta1**t)
        v_b_hat = v_b / (1 - beta2**t)

        weights -= learning_rate * m_w_hat / (np.sqrt(v_w_hat) + adam_eps)
        intercepts -= learning_rate * m_b_hat / (np.sqrt(v_b_hat) + adam_eps)

        final_grad_norm = float(max(np.max(np.abs(grad_w)), np.max(np.abs(grad_b))))
        if final_grad_norm < tol:
            break

    return FittedMultinomialModel(
        feature_names=tuple(feature_names),
        classes=tuple(classes),
        intercepts=tuple(intercepts.tolist()),
        coefficients=tuple(tuple(row.tolist()) for row in weights),
        feature_means=tuple(means.tolist()),
        feature_stds=tuple(stds_safe.tolist()),
        n_train=n,
        n_iterations=n_iterations,
        final_max_gradient_norm=final_grad_norm,
    )

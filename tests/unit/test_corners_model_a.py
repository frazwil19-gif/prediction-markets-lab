"""Corners Model A research helpers: distribution maths and the one-shot holdout guard."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cma", REPO / "scripts/corners_model_a.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def test_nb_pmf_normalises_and_reduces_to_poisson():
    mu = np.array([4.0, 6.5])
    assert np.allclose(M.nb_pmf_grid(mu, 0.08).sum(axis=1), 1, atol=1e-6)
    assert np.allclose(M.nb_pmf_grid(mu, 1e-7), M.nb_pmf_grid(mu, None), atol=1e-5)


def test_convolution_matches_poisson_sum():
    ph, pa = M.nb_pmf_grid(np.array([5.0]), None), M.nb_pmf_grid(np.array([4.0]), None)
    assert np.allclose(M.convolve_rows(ph, pa), M.nb_pmf_grid(np.array([9.0]), None), atol=1e-6)


def test_copula_rho_zero_close_to_independent_and_negative_rho_narrows_total():
    ph, pa = M.nb_pmf_grid(np.array([5.5]), 0.07), M.nb_pmf_grid(np.array([4.5]), 0.08)
    ind = M.convolve_rows(ph, pa)
    c0 = M.copula_total_pmf(ph, pa, 0.0)
    assert np.abs(c0 - ind).max() < 0.01
    var = lambda p: float((p * M.GRID ** 2).sum() - (p * M.GRID).sum() ** 2)
    assert var(M.copula_total_pmf(ph, pa, -0.2)) < var(ind)


def test_p_over_and_primary():
    pmf = M.nb_pmf_grid(np.array([10.0]), None)
    assert M.p_over(pmf, 9.5)[0] == pytest.approx(1 - pmf[0, :10].sum())
    assert M.primary_vec(pmf, np.array([12])).shape == (1,)


def test_holdout_guard_refuses_without_committed_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "OUT", tmp_path)
    with pytest.raises(SystemExit):
        M.mode_holdout(None)


def test_holdout_already_opened_in_repo():
    assert (REPO / "research/platform_v2/props_c1/corners/model_a/HOLDOUT_OPENED.marker").exists()

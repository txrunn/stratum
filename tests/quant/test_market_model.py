import numpy as np
import pandas as pd
import pytest

from stratum.quant.market_model import (
    MIN_ESTIMATION_OBSERVATIONS,
    compute_abnormal_returns,
    fit_market_model,
)


def _dates(n: int, start: str = "2024-01-02") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


def test_fit_market_model_recovers_known_alpha_beta_noiseless():
    n = 100
    idx = _dates(n)
    market = pd.Series(np.linspace(-0.01, 0.01, n), index=idx)
    true_alpha, true_beta = 0.0005, 1.5
    instrument = true_alpha + true_beta * market

    fit = fit_market_model(instrument, market)
    assert fit.alpha == pytest.approx(true_alpha, abs=1e-9)
    assert fit.beta == pytest.approx(true_beta, abs=1e-9)
    assert fit.residual_std == pytest.approx(0.0, abs=1e-9)
    assert fit.n_obs == n


def test_fit_market_model_raises_below_minimum_observations():
    n = MIN_ESTIMATION_OBSERVATIONS - 1
    idx = _dates(n)
    market = pd.Series(np.linspace(-0.01, 0.01, n), index=idx)
    instrument = 0.001 + 1.2 * market
    with pytest.raises(ValueError, match="need at least"):
        fit_market_model(instrument, market)


def test_fit_market_model_aligns_on_shared_index_only():
    # Instrument has two extra trailing observations the market series
    # lacks; they must be dropped before fitting, not treated as NaN-beta.
    n = 100
    idx = _dates(n)
    market = pd.Series(np.linspace(-0.01, 0.01, n), index=idx)
    instrument_core = 0.0 + 2.0 * market
    extra_idx = _dates(2, start="2025-01-02")
    instrument = pd.concat([instrument_core, pd.Series([0.5, 0.5], index=extra_idx)])

    fit = fit_market_model(instrument, market)
    assert fit.n_obs == n  # extra unmatched observations excluded
    assert fit.beta == pytest.approx(2.0, abs=1e-9)


def test_compute_abnormal_returns_matches_manual_calculation():
    n = 100
    idx = _dates(n)
    market = pd.Series(np.linspace(-0.01, 0.01, n), index=idx)
    instrument = 0.0002 + 1.1 * market + pd.Series(np.random.default_rng(42).normal(0, 0.0005, n), index=idx)
    fit = fit_market_model(instrument, market)

    event_idx = _dates(5, start="2024-06-03")
    market_window = pd.Series([0.001, -0.002, 0.0005, 0.003, -0.001], index=event_idx)
    instrument_window = pd.Series([0.005, 0.001, 0.002, 0.01, -0.002], index=event_idx)

    result = compute_abnormal_returns(fit, instrument_window, market_window)

    expected_predicted = fit.alpha + fit.beta * market_window
    expected_ar = instrument_window - expected_predicted
    expected_car = float(expected_ar.sum())
    expected_scar = expected_car / (fit.residual_std * np.sqrt(len(expected_ar)))

    pd.testing.assert_series_equal(result.abnormal_returns, expected_ar, check_names=False)
    assert result.car == pytest.approx(expected_car)
    assert result.scar == pytest.approx(expected_scar)


def test_compute_abnormal_returns_zero_residual_std_yields_zero_scar():
    n = 100
    idx = _dates(n)
    market = pd.Series(np.linspace(-0.01, 0.01, n), index=idx)
    instrument = 0.0 + 1.0 * market  # perfectly noiseless -> residual_std == 0
    fit = fit_market_model(instrument, market)
    assert fit.residual_std == pytest.approx(0.0, abs=1e-9)

    event_idx = _dates(3, start="2024-06-03")
    market_window = pd.Series([0.001, 0.002, 0.003], index=event_idx)
    instrument_window = market_window * 1.0  # also noiseless, fits the model exactly

    result = compute_abnormal_returns(fit, instrument_window, market_window)
    assert result.car == pytest.approx(0.0, abs=1e-9)
    assert result.scar == 0.0


def test_compute_abnormal_returns_raises_on_empty_window():
    n = 100
    idx = _dates(n)
    market = pd.Series(np.linspace(-0.01, 0.01, n), index=idx)
    instrument = 0.0 + 1.0 * market
    fit = fit_market_model(instrument, market)

    empty = pd.Series(dtype=float)
    with pytest.raises(ValueError, match="no paired observations"):
        compute_abnormal_returns(fit, empty, empty)

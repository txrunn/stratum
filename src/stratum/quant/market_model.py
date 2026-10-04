"""Market-model estimation and abnormal-return computation.

    r_it   = alpha_i + beta_i * r_mt + eps_it
    AR_it  = r_it - (alpha_hat_i + beta_hat_i * r_mt)
    CAR_i  = sum(AR_it)                  over the event window
    SCAR_i = CAR_i / (sigma_hat_eps_i * sqrt(n))   standardized by
                                                     estimation-window
                                                     residual vol

Estimation window is [-250, -30] trading days (see ARCHITECTURE.md
"quant/"), ending strictly before the event so the fit cannot see the
outcome. Standardizing is not optional: without it, a single volatile name
dominates any pooled mean (see event_study.py for pooling).

These are pure functions over pandas return Series — no store I/O, no
network. The store-backed version (pulling bars for an instrument/benchmark
pair and date range, then calling these) is deferred until a bars loader
exists (store/loaders/bars.py, not yet built); wiring it in later is a thin
query layer on top of this math, not a change to the math itself.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm

ESTIMATION_WINDOW = (-250, -30)  # trading-day offsets from t=0
MIN_ESTIMATION_OBSERVATIONS = 30


@dataclass(frozen=True)
class MarketModelFit:
    alpha: float
    beta: float
    residual_std: float
    n_obs: int


def fit_market_model(instrument_returns: pd.Series, market_returns: pd.Series) -> MarketModelFit:
    """OLS over the aligned intersection of the two series' index.

    Raises ValueError with fewer than MIN_ESTIMATION_OBSERVATIONS paired
    observations after alignment — not enough to estimate a stable beta,
    and a silently-degenerate fit is worse than an explicit failure here.
    """
    aligned = pd.concat(
        [instrument_returns.rename("r_i"), market_returns.rename("r_m")], axis=1
    ).dropna()
    if len(aligned) < MIN_ESTIMATION_OBSERVATIONS:
        raise ValueError(
            f"only {len(aligned)} paired observations; need at least "
            f"{MIN_ESTIMATION_OBSERVATIONS} to fit a market model"
        )
    design = sm.add_constant(aligned["r_m"])
    fitted = sm.OLS(aligned["r_i"], design).fit()
    return MarketModelFit(
        alpha=float(fitted.params["const"]),
        beta=float(fitted.params["r_m"]),
        residual_std=float(fitted.resid.std(ddof=2)),  # ddof=2: alpha and beta both estimated
        n_obs=len(aligned),
    )


@dataclass(frozen=True)
class EventWindowResult:
    abnormal_returns: pd.Series  # AR_it, indexed by date, over the event window
    car: float
    scar: float


def compute_abnormal_returns(
    fit: MarketModelFit,
    instrument_returns_window: pd.Series,
    market_returns_window: pd.Series,
) -> EventWindowResult:
    """AR/CAR/SCAR for one event, given a fit fom its estimation window and
    returns over its event window. SCAR is standardized by the
    *estimation*-window residual vol (`fit.residual_std`), never the event
    window's own — standardizing against the window you're testing would
    erase exactly the deviation you're trying to measure.
    """
    aligned = pd.concat(
        [instrument_returns_window.rename("r_i"), market_returns_window.rename("r_m")], axis=1
    ).dropna()
    if aligned.empty:
        raise ValueError("no paired observations in the event window")

    predicted = fit.alpha + fit.beta * aligned["r_m"]
    abnormal_returns = aligned["r_i"] - predicted
    car = float(abnormal_returns.sum())
    n = len(abnormal_returns)
    scar = 0.0 if fit.residual_std == 0 else car / (fit.residual_std * np.sqrt(n))
    return EventWindowResult(abnormal_returns=abnormal_returns, car=car, scar=scar)

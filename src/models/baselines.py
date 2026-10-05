"""Baseline forecasters. Each returns an (n_series, horizon) array from a (n_series, T) history."""
import warnings

import numpy as np


def seasonal_naive(history: np.ndarray, horizon: int, season: int = 7) -> np.ndarray:
    """Repeat the last `season` days (same weekday last week)."""
    last = history[:, -season:]
    reps = int(np.ceil(horizon / season))
    return np.tile(last, reps)[:, :horizon]


def moving_average(history: np.ndarray, horizon: int, window: int = 28) -> np.ndarray:
    m = np.nanmean(history[:, -window:], axis=1, keepdims=True)
    return np.repeat(m, horizon, axis=1)


def ets_holt_winters(history: np.ndarray, horizon: int, lookback: int = 365) -> np.ndarray:
    """Additive Holt-Winters (weekly seasonality) per series; falls back to MA on failure."""
    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    out = np.zeros((history.shape[0], horizon))
    fallback = moving_average(history, horizon)
    for i, y in enumerate(history):
        y = y[~np.isnan(y)][-lookback:]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ConvergenceWarning)
                warnings.simplefilter("ignore", RuntimeWarning)
                fit = ExponentialSmoothing(y, trend=None, seasonal="add", seasonal_periods=7,
                                           initialization_method="estimated").fit()
                out[i] = fit.forecast(horizon)
        except Exception:
            out[i] = fallback[i]
    return np.clip(np.nan_to_num(out, nan=0.0), 0, None)

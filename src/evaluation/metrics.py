"""Forecast accuracy metrics. All take arrays/Series of actuals and forecasts."""
import numpy as np
import pandas as pd


def wape(actual, forecast) -> float:
    """Weighted absolute percentage error: sum|e| / sum(actual). Robust to zeros."""
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    denom = a.sum()
    return float("nan") if denom == 0 else float(np.abs(f - a).sum() / denom)


def bias(actual, forecast) -> float:
    """Signed error as % of actuals: >0 means over-forecasting, <0 under-forecasting."""
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    denom = a.sum()
    return float("nan") if denom == 0 else float((f - a).sum() / denom)


def mae(actual, forecast) -> float:
    return float(np.abs(np.asarray(forecast, float) - np.asarray(actual, float)).mean())


def summarise(df: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """WAPE / bias / MAE / volume for a frame with `actual_units` and `forecast_units`."""
    def agg(g):
        return pd.Series({
            "wape": wape(g.actual_units, g.forecast_units),
            "bias": bias(g.actual_units, g.forecast_units),
            "mae": mae(g.actual_units, g.forecast_units),
            "units": g.actual_units.sum(),
            "abs_error": (g.forecast_units - g.actual_units).abs().sum(),
            "n": len(g),
        })
    if not by:
        return agg(df).to_frame().T
    return df.groupby(by).apply(agg, include_groups=False).reset_index()

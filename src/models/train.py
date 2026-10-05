"""Rolling-origin backtest of every model; writes predictions to {schema}.fact_forecast.

    python -m src.models.train            # all models, N_FOLDS rolling 28-day folds

Fold k forecasts the 28 days after cutoff c_k using ONLY data up to c_k (no random
splits). Models: seasonal naive, 28-day moving average, ETS (Holt-Winters),
LightGBM without event-lead features (`lightgbm_base`) and with them (`lightgbm`).
"""
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

from src.config import HORIZON, N_FOLDS, SCHEMA, connect
from src.features.build_features import BASE_FEATURES, EVENT_FEATURES, add_features, load_panel
from src.models import baselines

LGB_PARAMS = dict(objective="tweedie", tweedie_variance_power=1.2, learning_rate=0.05,
                  n_estimators=400, num_leaves=63, min_child_samples=50, subsample=0.8,
                  subsample_freq=1, colsample_bytree=0.8, verbose=-1, n_jobs=4, random_state=0)
LGB_MODELS = {"lightgbm_base": BASE_FEATURES, "lightgbm": BASE_FEATURES + EVENT_FEATURES}


def _fold_cutoffs(n_days: int) -> list[int]:
    """Last-observed day index for each fold (oldest first)."""
    return [n_days - HORIZON * k for k in range(N_FOLDS, 0, -1)]


def run_backtest(panel: pd.DataFrame) -> pd.DataFrame:
    feats = add_features(panel)
    dates = np.sort(feats["date"].unique())
    n_days = len(dates)
    keys = feats[["product_key", "store_key"]].drop_duplicates().reset_index(drop=True)
    n_series = len(keys)
    wide = feats.pivot(index=["product_key", "store_key"], columns="date", values="units")
    wide = wide.loc[list(map(tuple, keys.to_numpy()))]
    hist_all = wide.to_numpy()
    results = []
    for fold, cutoff in enumerate(_fold_cutoffs(n_days), start=1):
        t0 = time.time()
        target_dates = dates[cutoff:cutoff + HORIZON]
        actual = hist_all[:, cutoff:cutoff + HORIZON]
        hist = hist_all[:, :cutoff]
        preds = {
            "seasonal_naive": baselines.seasonal_naive(np.nan_to_num(hist), HORIZON),
            "moving_avg_28": baselines.moving_average(hist, HORIZON),
            "ets_holt_winters": baselines.ets_holt_winters(hist, HORIZON),
        }
        train = feats[(feats["date"] < dates[cutoff]) & feats["units"].notna()]
        test = feats[feats["date"].isin(target_dates)]
        for name, cols in LGB_MODELS.items():
            m = lgb.LGBMRegressor(**LGB_PARAMS).fit(train[cols], train["units"])
            test = test.assign(_p=np.clip(m.predict(test[cols]), 0, None))
            p = test.pivot(index=["product_key", "store_key"], columns="date", values="_p")
            preds[name] = p.loc[list(map(tuple, keys.to_numpy()))].to_numpy()
        for name, p in preds.items():
            frame = pd.DataFrame({
                "date": np.tile(target_dates, n_series),
                "product_key": np.repeat(keys.product_key.to_numpy(), HORIZON),
                "store_key": np.repeat(keys.store_key.to_numpy(), HORIZON),
                "model_name": name, "fold": fold,
                "horizon_day": np.tile(np.arange(1, HORIZON + 1), n_series),
                "forecast_units": p.reshape(-1),
                "actual_units": actual.reshape(-1),
            })
            results.append(frame)
        print(f"fold {fold}/{N_FOLDS} done in {time.time() - t0:.0f}s")
    out = pd.concat(results, ignore_index=True)
    out = out[out["actual_units"].notna()].copy()  # drop pre-launch (no actual) rows
    out["date_key"] = out["date"].dt.strftime("%Y%m%d").astype(int)
    out["abs_error"] = (out["forecast_units"] - out["actual_units"]).abs()
    return out[["date_key", "product_key", "store_key", "model_name", "fold", "horizon_day",
                "forecast_units", "actual_units", "abs_error"]]


def write_forecasts(con, df: pd.DataFrame) -> None:
    con.register("fc", df)
    con.execute(f"create or replace table {SCHEMA}.fact_forecast as select * from fc")
    # integrity check: every key must exist in the dimensions
    bad = con.execute(f"""
        select count(*) from {SCHEMA}.fact_forecast f
        left join {SCHEMA}.dim_date d using (date_key)
        left join {SCHEMA}.dim_product p using (product_key)
        left join {SCHEMA}.dim_store s using (store_key)
        where d.date_key is null or p.product_key is null or s.store_key is null""").fetchone()[0]
    assert bad == 0, f"{bad} forecast rows have orphan keys"
    print(f"{SCHEMA}.fact_forecast: {len(df):,} rows")


if __name__ == "__main__":
    con = connect()
    panel = load_panel(con)
    con.close()  # release DuckDB's thread pool before LightGBM/OpenMP starts (avoids a macOS segfault)
    forecasts = run_backtest(panel)
    con = connect()
    write_forecasts(con, forecasts)
    con.close()

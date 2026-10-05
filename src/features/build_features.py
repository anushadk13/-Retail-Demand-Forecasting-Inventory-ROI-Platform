"""Panel construction and leakage-safe feature engineering.

Every demand-derived feature is shifted by at least HORIZON days, so ONE model can
forecast all 28 days directly (no recursive feeding of its own predictions). Price,
calendar, SNAP and event features are known in advance, so they are used unshifted.
"""
import numpy as np
import pandas as pd

from src.config import HORIZON, SCHEMA

BASE_FEATURES = [
    "lag_28", "lag_35", "lag_42", "lag_364",
    "roll_mean_7", "roll_mean_28", "roll_mean_56", "roll_std_28",
    "price", "price_ratio", "price_change_7d",
    "dow", "month", "day_of_month", "snap_flag", "is_holiday",
    "store_code", "item_code", "dept_code", "cat_code",
]
# Pre-/post-holiday lead features: added after error analysis showed holiday weeks failing
EVENT_FEATURES = ["days_to_event", "days_since_event", "pre_holiday_window"]


def load_panel(con) -> pd.DataFrame:
    """Dense item x store x day panel (NaN units/price before an item's launch)."""
    df = con.execute(f"""
        select d.full_date as date, d.event_name, d.is_holiday,
               f.product_key, f.store_key, p.item_id, p.department, p.category, s.store_id,
               f.units_sold as units, pr.sell_price as price, f.snap_flag
        from {SCHEMA}.fact_sales f
        join {SCHEMA}.dim_date d using (date_key)
        join {SCHEMA}.dim_product p using (product_key)
        join {SCHEMA}.dim_store s using (store_key)
        join {SCHEMA}.dim_price pr using (price_key)
    """).df()
    df["date"] = pd.to_datetime(df["date"])
    cal = con.execute(f"select full_date as date, event_name from {SCHEMA}.dim_date").df()
    cal["date"] = pd.to_datetime(cal["date"])
    series = df[["product_key", "store_key", "item_id", "department", "category", "store_id"]
                ].drop_duplicates()
    grid = series.merge(cal[["date"]], how="cross")
    out = grid.merge(df[["date", "product_key", "store_key", "units", "price", "snap_flag"]],
                     on=["date", "product_key", "store_key"], how="left")
    out = out.merge(cal, on="date", how="left")
    out["is_holiday"] = out["event_name"].notna()
    return out.sort_values(["product_key", "store_key", "date"]).reset_index(drop=True)


def _event_distance_features(dates: pd.Series, event_dates: np.ndarray) -> pd.DataFrame:
    d = dates.to_numpy().astype("datetime64[D]")
    ev = np.sort(event_dates.astype("datetime64[D]"))
    nxt = np.searchsorted(ev, d, side="left")  # first event >= d
    prv = np.searchsorted(ev, d, side="right") - 1  # last event <= d
    big = 99
    to_next = np.where(nxt < len(ev), (ev[np.minimum(nxt, len(ev) - 1)] - d).astype(int), big)
    since = np.where(prv >= 0, (d - ev[np.maximum(prv, 0)]).astype(int), big)
    out = pd.DataFrame({"days_to_event": np.minimum(to_next, 14),
                        "days_since_event": np.minimum(since, 14)})
    out["pre_holiday_window"] = (out["days_to_event"] <= 3).astype(int)
    return out


def add_features(panel: pd.DataFrame, horizon: int = HORIZON) -> pd.DataFrame:
    df = panel.copy()
    g = df.groupby(["product_key", "store_key"], sort=False)
    u = g["units"]
    for lag in (horizon, horizon + 7, horizon + 14, 364):
        df[f"lag_{lag}"] = u.shift(lag)
    shifted = u.shift(horizon)
    gs = shifted.groupby([df["product_key"], df["store_key"]], sort=False)
    for w in (7, 28, 56):
        df[f"roll_mean_{w}"] = gs.transform(lambda s, w=w: s.rolling(w, min_periods=1).mean())
    df["roll_std_28"] = gs.transform(lambda s: s.rolling(28, min_periods=2).std())
    gp = df.groupby(["product_key", "store_key"], sort=False)["price"]
    med = gp.transform(lambda s: s.rolling(91, min_periods=1).median())
    df["price_ratio"] = df["price"] / med
    df["price_change_7d"] = df["price"] / gp.shift(7) - 1
    df["dow"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["day_of_month"] = df["date"].dt.day
    df["snap_flag"] = df["snap_flag"].fillna(0).astype(int)
    df["is_holiday"] = df["is_holiday"].astype(int)
    for col, name in [("store_id", "store_code"), ("item_id", "item_code"),
                      ("department", "dept_code"), ("category", "cat_code")]:
        df[name] = df[col].astype("category").cat.codes
    ev_dates = df.loc[df["event_name"].notna(), "date"].unique().to_numpy()
    # pre_holiday_window etc. are calendar-only: compute once on unique dates, then merge
    uniq = pd.Series(df["date"].unique().to_numpy())
    ef = _event_distance_features(uniq, ev_dates)
    ef["date"] = uniq.to_numpy()
    df = df.merge(ef, on="date", how="left")
    return df

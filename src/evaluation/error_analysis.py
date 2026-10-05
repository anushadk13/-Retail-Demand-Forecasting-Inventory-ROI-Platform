"""Slice forecast error by segment to find WHERE the model fails."""
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf

from src.config import SCHEMA
from src.evaluation.metrics import summarise


def load_enriched(con) -> pd.DataFrame:
    """fact_forecast joined to dims + price band, SNAP, holiday window and slow-mover flag."""
    df = con.execute(f"""
        select f.*, d.full_date as date, d.is_holiday, d.event_name,
               p.item_id, p.category, p.department, s.store_id, s.state,
               pr.price_band, fs.snap_flag,
               avg(fs2.units) over (partition by f.product_key, f.store_key) as series_mean
        from {SCHEMA}.fact_forecast f
        join {SCHEMA}.dim_date d using (date_key)
        join {SCHEMA}.dim_product p using (product_key)
        join {SCHEMA}.dim_store s using (store_key)
        left join {SCHEMA}.fact_sales fs using (date_key, product_key, store_key)
        left join {SCHEMA}.dim_price pr on fs.price_key = pr.price_key
        left join (select product_key, store_key, avg(units_sold) as units
                   from {SCHEMA}.fact_sales group by 1, 2) fs2
               using (product_key, store_key)
    """).df()
    df["date"] = pd.to_datetime(df["date"])
    ev_df = con.execute(
        f"select full_date from {SCHEMA}.dim_date where event_name is not null").df()
    ev = np.sort(pd.to_datetime(ev_df["full_date"]).to_numpy().astype("datetime64[D]"))
    d = df["date"].to_numpy().astype("datetime64[D]")
    nxt = np.searchsorted(ev, d, side="left")
    gap = np.where(nxt < len(ev), (ev[np.minimum(nxt, len(ev) - 1)] - d).astype(int), 999)
    df["holiday_week"] = gap <= 7  # the event day itself or the 7 days leading into it
    df["slow_mover"] = df["series_mean"] < 1.0
    df["promo_day"] = df["price_band"] == "promo"
    df["snap_flag"] = df["snap_flag"].fillna(0).astype(bool)
    return df


def segment_table(df: pd.DataFrame, model: str) -> pd.DataFrame:
    d = df[df["model_name"] == model]
    parts = []
    for cat in sorted(d["category"].unique()):
        parts.append((f"Category: {cat}", d[d["category"] == cat]))
    parts += [
        ("Holiday weeks", d[d["holiday_week"]]),
        ("Non-holiday weeks", d[~d["holiday_week"]]),
        ("Slow movers (<1 unit/day)", d[d["slow_mover"]]),
        ("Fast movers (>=1 unit/day)", d[~d["slow_mover"]]),
        ("Price promotion days", d[d["promo_day"]]),
        ("SNAP days", d[d["snap_flag"]]),
    ]
    rows = []
    total_err = (d["forecast_units"] - d["actual_units"]).abs().sum()
    for name, g in parts:
        s = summarise(g).iloc[0]
        rows.append({"segment": name, "wape": s.wape, "bias": s.bias,
                     "share_of_rows": len(g) / len(d),
                     "share_of_abs_error": s.abs_error / total_err})
    return pd.DataFrame(rows)


def category_x_holiday(df: pd.DataFrame, model: str) -> pd.DataFrame:
    d = df[df["model_name"] == model]
    t = summarise(d, ["category", "holiday_week"])
    total = t["abs_error"].sum()
    t["share_of_total_error"] = t["abs_error"] / total
    return t


def residual_autocorrelation(df: pd.DataFrame, model: str, nlags: int = 14) -> pd.Series:
    """ACF of the total daily residual (fold-wise to avoid stitching folds together)."""
    d = df[df["model_name"] == model].copy()
    d["resid"] = d["actual_units"] - d["forecast_units"]
    daily = d.groupby(["fold", "date"])["resid"].sum().reset_index()
    vals = []
    for _, g in daily.groupby("fold"):
        vals.append(acf(g.sort_values("date")["resid"], nlags=nlags, fft=False))
    return pd.Series(np.mean(vals, axis=0), name="acf")


def holiday_uplift(df: pd.DataFrame, model_a: str, model_b: str) -> dict:
    """Compare holiday-week WAPE of two models (e.g. before/after adding event features)."""
    out = {}
    for m in (model_a, model_b):
        g = df[(df["model_name"] == m) & df["holiday_week"]]
        out[m] = summarise(g).iloc[0].wape
    return out

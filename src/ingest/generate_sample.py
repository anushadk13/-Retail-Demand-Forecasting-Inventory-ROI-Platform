"""Generate a synthetic dataset in the exact M5 file format (calendar / sell_prices / sales wide).

The real M5 data needs a Kaggle login, so this lets the whole pipeline run offline. The
demand process deliberately contains the effects the error analysis should discover:
weekly + yearly seasonality, pre-holiday spikes (strongest for FOODS), SNAP-day lift,
price elasticity during promotions, intermittent slow movers, and closed stores on Dec 25.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import SAMPLE_DIR

STORES = ["CA_1", "CA_2", "CA_3", "CA_4", "TX_1", "TX_2", "TX_3", "WI_1", "WI_2", "WI_3"]
DEPTS = {"FOODS_1": "FOODS", "FOODS_2": "FOODS", "FOODS_3": "FOODS",
         "HOBBIES_1": "HOBBIES", "HOBBIES_2": "HOBBIES",
         "HOUSEHOLD_1": "HOUSEHOLD", "HOUSEHOLD_2": "HOUSEHOLD"}
# category -> (median daily rate, pre-holiday lift, base price)
CAT_PARAMS = {"FOODS": (3.0, 0.9, 3.5), "HOBBIES": (1.0, 0.35, 6.0), "HOUSEHOLD": (1.8, 0.25, 8.0)}
SLOW_SHARE = 0.25  # share of items that are intermittent slow movers


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> pd.Timestamp:
    d = pd.Timestamp(year, month, 1)
    d += pd.Timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))
    return d


def _events(year: int) -> dict[pd.Timestamp, tuple[str, str]]:
    last_may = pd.Timestamp(year, 5, 31)
    memorial = last_may - pd.Timedelta(days=last_may.weekday())
    return {
        pd.Timestamp(year, 1, 1): ("NewYear", "National"),
        pd.Timestamp(year, 2, 14): ("ValentinesDay", "Cultural"),
        memorial: ("MemorialDay", "National"),
        pd.Timestamp(year, 7, 4): ("IndependenceDay", "National"),
        _nth_weekday(year, 9, 0, 1): ("LaborDay", "National"),
        pd.Timestamp(year, 10, 31): ("Halloween", "Cultural"),
        _nth_weekday(year, 11, 3, 4): ("Thanksgiving", "National"),
        pd.Timestamp(year, 12, 25): ("Christmas", "National"),
    }


def make_calendar(start: str, n_days: int) -> pd.DataFrame:
    dates = pd.date_range(start, periods=n_days)
    events = {}
    for y in range(dates[0].year, dates[-1].year + 1):
        events.update(_events(y))
    cal = pd.DataFrame({"date": dates})
    cal["wm_yr_wk"] = 11000 + (cal.index // 7)
    cal["weekday"] = cal["date"].dt.day_name()
    cal["wday"] = cal["date"].dt.dayofweek + 1
    cal["month"] = cal["date"].dt.month
    cal["year"] = cal["date"].dt.year
    cal["d"] = [f"d_{i + 1}" for i in range(n_days)]
    cal["event_name_1"] = cal["date"].map(lambda d: events.get(d, (None, None))[0])
    cal["event_type_1"] = cal["date"].map(lambda d: events.get(d, (None, None))[1])
    cal["event_name_2"] = None
    cal["event_type_2"] = None
    # SNAP days: state-specific windows within each month
    day = cal["date"].dt.day
    cal["snap_CA"] = ((day >= 1) & (day <= 10)).astype(int)
    cal["snap_TX"] = day.isin([1, 3, 5, 6, 8, 9, 11, 12, 14, 15]).astype(int)
    cal["snap_WI"] = ((day >= 2) & (day <= 11)).astype(int)
    cal["date"] = cal["date"].dt.strftime("%Y-%m-%d")
    return cal


def generate(out_dir: Path, n_items_per_dept: int = 8, n_days: int = 1000,
             start: str = "2021-01-01", seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    cal = make_calendar(start, n_days)
    dates = pd.to_datetime(cal["date"])
    dow = dates.dt.dayofweek.to_numpy()
    doy = dates.dt.dayofyear.to_numpy()
    is_event = cal["event_name_1"].notna().to_numpy()
    # pre-holiday window: 1-3 days before an event, ramping up to the day itself
    ev_idx = np.flatnonzero(is_event)
    pre = np.zeros(n_days)
    for i in ev_idx:
        for k, w in enumerate([1.0, 0.7, 0.4, 0.2]):  # event day, 1d, 2d, 3d before
            if i - k >= 0:
                pre[i - k] = max(pre[i - k], w)
    christmas = (cal["event_name_1"] == "Christmas").to_numpy()
    wk = cal["wm_yr_wk"].to_numpy()
    n_weeks = wk.max() - wk.min() + 1

    items, rows, price_rows = [], [], []
    for dept, cat in DEPTS.items():
        for j in range(1, n_items_per_dept + 1):
            items.append((f"{dept}_{j:03d}", dept, cat))

    for item_id, dept, cat in items:
        med_rate, hol_lift, base_price = CAT_PARAMS[cat]
        slow = rng.random() < SLOW_SHARE
        item_rate = rng.lognormal(np.log(0.35 if slow else med_rate), 0.5)
        item_price = base_price * rng.lognormal(0, 0.35)
        dow_profile = 1 + rng.uniform(0.1, 0.35) * np.array([-0.3, -0.2, -0.1, 0, 0.2, 0.9, 0.7])
        yr_phase = rng.uniform(0, 2 * np.pi)
        launch_week = int(rng.integers(0, 6)) if rng.random() < 0.3 else 0  # staggered launches
        trend = rng.normal(0, 0.12)
        for store in STORES:
            state = store[:2]
            store_mult = rng.lognormal(0, 0.3)
            # weekly price path with promotions (15-30% off, ~8% of weeks)
            promo = rng.random(n_weeks) < 0.08
            wk_price = item_price * (1 + rng.normal(0, 0.01, n_weeks))
            wk_price = np.where(promo, wk_price * rng.uniform(0.70, 0.85, n_weeks), wk_price)
            wk_price = np.round(wk_price, 2)
            price_d = wk_price[wk - wk.min()]
            promo_d = promo[wk - wk.min()]
            snap = cal[f"snap_{state}"].to_numpy()
            lam = (item_rate * store_mult * dow_profile[dow]
                   * (1 + 0.2 * np.sin(2 * np.pi * doy / 365.25 + yr_phase))
                   * (1 + trend * np.arange(n_days) / n_days)
                   * (1 + hol_lift * pre)
                   * (1 + (0.15 if cat == "FOODS" else 0.03) * snap)
                   * np.where(promo_d, (item_price / price_d) ** 1.8, 1.0))
            lam = np.where(christmas, 0.0, lam)
            sales = rng.negative_binomial(n=3, p=3 / (3 + lam + 1e-9)) if not slow else rng.poisson(lam)
            sales = np.where(christmas, 0, sales)
            first_day = launch_week * 7
            sales[:first_day] = 0
            rows.append([f"{item_id}_{store}_evaluation", item_id, dept, cat, store, state, *sales])
            for w in range(launch_week, n_weeks):
                price_rows.append((store, item_id, wk.min() + w, wk_price[w]))

    sales_df = pd.DataFrame(rows, columns=["id", "item_id", "dept_id", "cat_id", "store_id",
                                           "state_id"] + list(cal["d"]))
    prices = pd.DataFrame(price_rows, columns=["store_id", "item_id", "wm_yr_wk", "sell_price"])
    cal.to_csv(out_dir / "calendar.csv", index=False)
    prices.to_csv(out_dir / "sell_prices.csv", index=False)
    sales_df.to_csv(out_dir / "sales_train_evaluation.csv", index=False)
    print(f"Wrote {len(sales_df)} series x {n_days} days to {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=SAMPLE_DIR)
    ap.add_argument("--days", type=int, default=1000)
    ap.add_argument("--items-per-dept", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    generate(a.out, a.items_per_dept, a.days, seed=a.seed)

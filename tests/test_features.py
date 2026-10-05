import numpy as np
import pandas as pd

from src.features.build_features import BASE_FEATURES, EVENT_FEATURES, add_features


def _panel(n_days=500, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-01", periods=n_days)
    rows = []
    for pk in (1, 2):
        rows.append(pd.DataFrame({
            "date": dates, "product_key": pk, "store_key": 1, "item_id": f"I{pk}",
            "department": "FOODS_1", "category": "FOODS", "store_id": "CA_1",
            "units": rng.poisson(3, n_days).astype(float), "price": 2.0 + 0.0 * np.arange(n_days),
            "snap_flag": 0, "event_name": [("Xmas" if d.month == 12 and d.day == 25 else None) for d in dates],
        }))
    p = pd.concat(rows, ignore_index=True)
    p["is_holiday"] = p["event_name"].notna()
    return p


def test_all_feature_columns_exist():
    f = add_features(_panel())
    assert set(BASE_FEATURES + EVENT_FEATURES) <= set(f.columns)


def test_lag_alignment():
    p = _panel()
    f = add_features(p).sort_values(["product_key", "date"]).reset_index(drop=True)
    s = f[f.product_key == 1].reset_index(drop=True)
    assert s.loc[100, "lag_28"] == s.loc[72, "units"]


def test_no_leakage_demand_features_ignore_last_horizon_days():
    """Changing demand at day t must not change any demand feature for days t..t+27."""
    p = _panel()
    t = 300
    p2 = p.copy()
    idx = p2[(p2.product_key == 1)].index[t]
    p2.loc[idx, "units"] += 1000
    a = add_features(p).sort_values(["product_key", "date"]).reset_index(drop=True)
    b = add_features(p2).sort_values(["product_key", "date"]).reset_index(drop=True)
    demand_cols = ["lag_28", "lag_35", "lag_42", "lag_364", "roll_mean_7", "roll_mean_28",
                   "roll_mean_56", "roll_std_28"]
    s_a, s_b = a[a.product_key == 1].reset_index(drop=True), b[b.product_key == 1].reset_index(drop=True)
    window = slice(t, t + 27)  # .loc is inclusive: days t .. t+27
    pd.testing.assert_frame_equal(s_a.loc[window, demand_cols], s_b.loc[window, demand_cols])


def test_event_features_count_down_to_event():
    f = add_features(_panel())
    day_before = f[(f.product_key == 1) & (f.date == "2021-12-24")].iloc[0]
    assert day_before.days_to_event == 1 and day_before.pre_holiday_window == 1

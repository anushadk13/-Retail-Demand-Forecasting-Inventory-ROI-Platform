import pandas as pd

from src.ingest.generate_sample import generate, make_calendar


def test_calendar_columns_match_m5():
    cal = make_calendar("2021-01-01", 400)
    for c in ["date", "wm_yr_wk", "weekday", "wday", "month", "year", "d", "event_name_1",
              "event_type_1", "snap_CA", "snap_TX", "snap_WI"]:
        assert c in cal.columns
    assert cal.loc[cal.event_name_1 == "Christmas"].shape[0] == 1


def test_generate_shapes_and_christmas_closed(tmp_path):
    generate(tmp_path, n_items_per_dept=1, n_days=400, seed=1)
    sales = pd.read_csv(tmp_path / "sales_train_evaluation.csv")
    cal = pd.read_csv(tmp_path / "calendar.csv")
    assert len(sales) == 7 * 10
    xmas = cal.loc[cal.event_name_1 == "Christmas", "d"].iloc[0]
    assert (sales[xmas] == 0).all()
    assert (sales.filter(like="d_") >= 0).all().all()
    prices = pd.read_csv(tmp_path / "sell_prices.csv")
    assert (prices.sell_price > 0).all()

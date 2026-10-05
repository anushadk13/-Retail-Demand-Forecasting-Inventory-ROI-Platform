import numpy as np
import pandas as pd

from src.evaluation.metrics import bias, mae, summarise, wape


def test_wape_basic():
    assert wape([10, 10], [8, 14]) == (2 + 4) / 20


def test_wape_zero_actuals_is_nan():
    assert np.isnan(wape([0, 0], [1, 1]))


def test_bias_sign():
    assert bias([10, 10], [12, 12]) > 0  # over-forecast
    assert bias([10, 10], [5, 5]) < 0  # under-forecast


def test_mae():
    assert mae([1, 2, 3], [2, 2, 5]) == 1.0


def test_summarise_groups():
    df = pd.DataFrame({"g": ["a", "a", "b"], "actual_units": [10, 10, 5],
                       "forecast_units": [10, 10, 10]})
    out = summarise(df, ["g"]).set_index("g")
    assert out.loc["a", "wape"] == 0 and out.loc["b", "wape"] == 1

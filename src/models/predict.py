"""Print the headline model comparison from the forecasts already written by train.py."""
import pandas as pd

from src.config import SCHEMA, connect
from src.evaluation.metrics import summarise

ORDER = ["seasonal_naive", "moving_avg_28", "ets_holt_winters", "lightgbm_base", "lightgbm"]


def model_comparison(con) -> pd.DataFrame:
    df = con.execute(f"select * from {SCHEMA}.fact_forecast").df()
    t = summarise(df, ["model_name"]).set_index("model_name").loc[ORDER]
    base = t.loc["seasonal_naive", "wape"]
    t["improvement_vs_naive"] = 1 - t["wape"] / base
    return t[["wape", "bias", "mae", "improvement_vs_naive"]]


if __name__ == "__main__":
    pd.options.display.float_format = "{:.4f}".format
    print(model_comparison(connect(read_only=True)))

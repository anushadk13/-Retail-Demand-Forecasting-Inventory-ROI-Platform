"""Export BI-ready CSVs (Power BI / Tableau sources) and render static dashboard charts.

Charts follow one palette (blue = LightGBM, orange = baseline, grey = other) and are labelled
directly so they do not rely on colour alone.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import EXPORT_DIR, IMAGE_DIR, SCHEMA, connect  # noqa: E402
from src.evaluation.error_analysis import load_enriched, segment_table  # noqa: E402
from src.evaluation.metrics import summarise  # noqa: E402
from src.models.predict import ORDER, model_comparison  # noqa: E402

BLUE, ORANGE, GREY, INK, MUTED = "#2a78d6", "#eb6834", "#a8a8a3", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": MUTED, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.titleweight": "bold", "axes.titlecolor": INK,
                     "axes.titlelocation": "left", "figure.facecolor": "white"})


def stockout_risk(con, model="lightgbm", days=7) -> pd.DataFrame:
    """Items whose next-`days` forecast demand exceeds simulated stock on hand (latest fold)."""
    return con.execute(f"""
        with last as (select max(fold) as f from {SCHEMA}.fact_forecast),
        demand as (
            select product_key, store_key, sum(forecast_units) as forecast_demand
            from {SCHEMA}.fact_forecast, last
            where model_name = '{model}' and fold = last.f and horizon_day <= {days}
            group by 1, 2)
        select p.item_id, p.category, s.store_id, i.stock_on_hand,
               round(d.forecast_demand, 1) as forecast_{days}d_demand,
               round(d.forecast_demand - i.stock_on_hand, 1) as shortfall_units
        from demand d
        join {SCHEMA}.fact_inventory i using (product_key, store_key)
        join {SCHEMA}.dim_product p using (product_key)
        join {SCHEMA}.dim_store s using (store_key)
        where d.forecast_demand > i.stock_on_hand
        order by shortfall_units desc""").df()


def _save(fig, name):
    IMAGE_DIR.mkdir(exist_ok=True)
    fig.savefig(IMAGE_DIR / name, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    con = connect(read_only=True)
    df = load_enriched(con)
    df["week"] = df["date"].dt.to_period("W").dt.start_time
    full = df.groupby("week")["date"].nunique()
    dfw = df[df["week"].isin(full[full == 7].index)]  # weekly views drop partial edge weeks

    weekly = (dfw[dfw.model_name == "lightgbm"].groupby(["week", "category"])
              [["forecast_units", "actual_units"]].sum().reset_index())
    weekly.to_csv(EXPORT_DIR / "forecast_vs_actual_weekly.csv", index=False)
    trend = summarise(dfw, ["model_name", "week"])[["model_name", "week", "wape", "bias"]]
    trend.to_csv(EXPORT_DIR / "accuracy_trend_weekly.csv", index=False)
    seg = pd.concat([segment_table(df, m).assign(model_name=m) for m in ORDER])
    seg.to_csv(EXPORT_DIR / "error_by_segment.csv", index=False)
    risk = stockout_risk(con)
    risk.to_csv(EXPORT_DIR / "stockout_risk.csv", index=False)
    cmp_ = model_comparison(con)
    cmp_.to_csv(EXPORT_DIR / "model_comparison.csv")

    # Chart 1: model comparison
    fig, ax = plt.subplots(figsize=(7, 3.4))
    colors = [BLUE if m == "lightgbm" else (ORANGE if m == "seasonal_naive" else GREY) for m in cmp_.index]
    bars = ax.barh(cmp_.index[::-1], cmp_["wape"][::-1] * 100, color=colors[::-1], height=0.55)
    for b, v in zip(bars, cmp_["wape"][::-1] * 100):
        ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", color=INK)
    ax.set_xlabel("WAPE (%, lower is better) - 13 rolling 28-day folds")
    ax.set_title("LightGBM cuts WAPE ~27% vs the seasonal-naive baseline", fontsize=11)
    ax.set_xlim(0, 108)
    _save(fig, "model_comparison.png")

    # Chart 2: forecast vs actual weekly (all categories)
    w = weekly.groupby("week")[["forecast_units", "actual_units"]].sum()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.plot(w.index, w.actual_units, color=INK, lw=2, label="Actual")
    ax.plot(w.index, w.forecast_units, color=BLUE, lw=2, label="LightGBM forecast")
    ax.set_ylabel("Units per week")
    ax.set_title("Weekly forecast vs actual, all stores (backtest year)", fontsize=11)
    ax.legend(frameon=False, loc="lower left", ncol=2)
    _save(fig, "forecast_vs_actual.png")

    # Chart 3: error by segment, baseline vs final model
    s = pd.concat([segment_table(df, m).assign(model_name=m) for m in ("moving_avg_28", "lightgbm")])
    p = s.pivot(index="segment", columns="model_name", values="wape").sort_values("lightgbm")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = range(len(p))
    ax.barh([i + 0.2 for i in y], p["moving_avg_28"] * 100, height=0.38, color=ORANGE, label="28-day moving avg")
    ax.barh([i - 0.2 for i in y], p["lightgbm"] * 100, height=0.38, color=BLUE, label="LightGBM")
    ax.set_yticks(list(y))
    ax.set_yticklabels(p.index)
    ax.set_xlabel("WAPE (%)")
    ax.set_title("Where the error is: slow movers and HOBBIES are hardest", fontsize=11)
    ax.legend(frameon=False, loc="lower right")
    _save(fig, "error_by_segment.png")

    # Chart 4: weekly WAPE trend (drift indicator)
    t = trend[trend.model_name == "lightgbm"]
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(t.week, t.wape * 100, color=BLUE, lw=2)
    ax.set_ylabel("Weekly WAPE (%)")
    ax.set_title("Forecast accuracy trend (LightGBM)", fontsize=11)
    _save(fig, "accuracy_trend.png")
    print(f"exports -> {EXPORT_DIR}; charts -> {IMAGE_DIR}; stockout-risk rows: {len(risk)}")


if __name__ == "__main__":
    main()

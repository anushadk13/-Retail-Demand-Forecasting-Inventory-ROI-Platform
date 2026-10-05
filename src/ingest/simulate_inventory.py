"""M5 has no inventory data, so stock-on-hand is SIMULATED (seeded) from recent sales.

Used only by the stockout-risk list and alert. Stock is a random multiple of one week of
recent demand, so a realistic share of items sit below forecast demand.
"""
import numpy as np


def simulate_inventory(con, seed: int = 7) -> None:
    cols = [r[0] for r in con.execute("describe raw.sales_wide").fetchall() if r[0].startswith("d_")]
    last28 = cols[-28:]
    expr = " + ".join(f'"{c}"' for c in last28)
    df = con.execute(
        f"select item_id, store_id, ({expr}) / 28.0 as mean_28d from raw.sales_wide").df()
    rng = np.random.default_rng(seed)
    df["stock_on_hand"] = np.round(df["mean_28d"] * 7 * rng.uniform(0.4, 1.8, len(df))).astype(int)
    con.register("inv_df", df[["item_id", "store_id", "stock_on_hand"]])
    con.execute("create or replace table raw.inventory_snapshot as select * from inv_df")
    print(f"raw.inventory_snapshot: {len(df):,} rows (simulated)")

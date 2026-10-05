"""Load the raw M5-format CSVs into the warehouse `raw` schema (the 'E' and 'L' of ELT).

    python -m src.ingest.load_raw --sample     # synthetic data in data/sample
    python -m src.ingest.load_raw              # real M5 data in data/raw
"""
import argparse
import sys

from src.config import RAW_DIR, SAMPLE_DIR, connect
from src.ingest.simulate_inventory import simulate_inventory

FILES = {
    "calendar": "calendar.csv",
    "sell_prices": "sell_prices.csv",
    "sales_wide": "sales_train_evaluation.csv",
}


def load(sample: bool) -> None:
    src_dir = SAMPLE_DIR if sample else RAW_DIR
    missing = [f for f in FILES.values() if not (src_dir / f).exists()]
    if missing:
        hint = ("python -m src.ingest.generate_sample" if sample
                else "kaggle competitions download -c m5-forecasting-accuracy -p data/raw")
        sys.exit(f"Missing {missing} in {src_dir}. Try: {hint}")
    con = connect()
    con.execute("create schema if not exists raw")
    for table, fname in FILES.items():
        path = (src_dir / fname).as_posix()
        con.execute(f"create or replace table raw.{table} as "
                    f"select * from read_csv_auto('{path}', sample_size=-1)")
        n = con.execute(f"select count(*) from raw.{table}").fetchone()[0]
        print(f"raw.{table}: {n:,} rows")
    simulate_inventory(con)
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="load data/sample instead of data/raw")
    load(ap.parse_args().sample)

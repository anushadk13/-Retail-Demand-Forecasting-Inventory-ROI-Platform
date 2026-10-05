"""Pull US public holidays from the free Nager.Date API into raw.external_holidays.

This is the code equivalent of the low-code flow in integrations/n8n_holiday_ingest.json.
"""
import sys

import pandas as pd
import requests

from src.config import connect

URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/US"


def fetch(years: list[int]) -> pd.DataFrame:
    frames = []
    for y in years:
        r = requests.get(URL.format(year=y), timeout=15)
        r.raise_for_status()
        frames.append(pd.DataFrame(r.json()))
    df = pd.concat(frames, ignore_index=True)
    return df[["date", "localName", "name", "global"]].rename(
        columns={"localName": "local_name", "global": "is_global"})


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or [2021, 2022, 2023]
    df = fetch(years)
    con = connect()
    con.execute("create schema if not exists raw")
    con.register("h", df)
    con.execute("create or replace table raw.external_holidays as select * from h")
    print(f"raw.external_holidays: {len(df)} rows")

"""Drift and stockout alerts (code twin of integrations/n8n_alerts.json).

    python -m src.alerts.alerts            # prints alerts, or POSTs to ALERT_WEBHOOK_URL
"""
import os

import requests

from src.config import SCHEMA, connect


def drift_alerts(con, model="lightgbm", window=7, threshold=None) -> list[str]:
    threshold = threshold or float(os.getenv("DRIFT_WAPE_THRESHOLD", 0.80))
    df = con.execute(f"""
        select date_key, sum(actual_units) as a, sum(abs_error) as e
        from {SCHEMA}.fact_forecast
        where model_name = '{model}' and fold = (select max(fold) from {SCHEMA}.fact_forecast)
        group by 1 order by 1""").df()
    last = df.tail(window)
    value = last.e.sum() / last.a.sum()
    if value > threshold:
        return [f"DRIFT: rolling {window}-day WAPE of {model} is {value:.1%} (> {threshold:.0%})"]
    return []


def stockout_alerts(con, top_n=10) -> list[str]:
    from src.reporting.export_bi import stockout_risk
    risk = stockout_risk(con).head(top_n)
    return [f"STOCKOUT RISK: {r.item_id} @ {r.store_id}: 7d forecast {r.forecast_7d_demand:.0f} "
            f"vs stock {r.stock_on_hand} (short {r.shortfall_units:.0f})" for r in risk.itertuples()]


def send(messages: list[str]) -> None:
    if not messages:
        print("No alerts.")
        return
    url = os.getenv("ALERT_WEBHOOK_URL")
    text = "\n".join(messages)
    if url:
        requests.post(url, json={"text": text}, timeout=15).raise_for_status()
        print(f"Sent {len(messages)} alerts to webhook.")
    else:
        print(text)


if __name__ == "__main__":
    con = connect(read_only=True)
    send(drift_alerts(con) + stockout_alerts(con))

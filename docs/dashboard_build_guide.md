# Building the Power BI and Tableau dashboards

`.pbix` / `.twbx` files are produced in the BI tools themselves, so they are **not** in the repo. Everything needed is exported by `make report` into `reports/exports/`; static previews are in `images/`.

## Data sources
| File | Grain | Use |
|---|---|---|
| `forecast_vs_actual_weekly.csv` | week x category | forecast vs actual lines |
| `accuracy_trend_weekly.csv` | week x model | accuracy trend / drift indicator |
| `error_by_segment.csv` | model x segment | executive error breakdown |
| `stockout_risk.csv` | item x store | operations stockout list (stock is **simulated**) |
| `model_comparison.csv` | model | KPI cards |

Alternatively connect directly to the warehouse tables `dev.fact_sales`, `dev.fact_forecast`, `dev.dim_*` (DuckDB ODBC driver, or Postgres if you swap the warehouse).

## Power BI - operations dashboard
1. Import the CSVs (or the star schema; relate `fact_*` to `dim_*` on the `*_key` columns).
2. Page 1: line chart forecast vs actual (axis `week`, legend `category`); slicers for category and store.
3. Page 2: table of `stockout_risk.csv` sorted by `shortfall_units`, conditional bar on shortfall.
4. Page 3: line chart of weekly WAPE with a constant line at the alert threshold (0.80).

## Tableau Public - executive view
KPI tiles from `model_comparison.csv` (WAPE, improvement vs naive); horizontal bars of WAPE by segment from `error_by_segment.csv` (filter model = lightgbm, moving_avg_28); publish to Tableau Public and put the link in the README.

PY ?= .venv/bin/python
DBT = cd dbt_project && ../.venv/bin/dbt
export WAREHOUSE_PATH ?= $(CURDIR)/warehouse/retail.duckdb

.PHONY: setup sample load dbt train report roi alerts notebooks test lint all clean

setup:
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

sample:            ## generate synthetic M5-format data
	$(PY) -m src.ingest.generate_sample

load:              ## raw CSVs -> warehouse (use SAMPLE=1 for data/sample)
	$(PY) -m src.ingest.load_raw $(if $(SAMPLE),--sample,)

dbt:               ## build star schema + run data tests
	$(DBT) build --profiles-dir . --target dev

train:             ## backtest all models, write fact_forecast
	$(PY) -m src.models.train
	$(PY) -m src.models.predict

report:            ## BI exports + charts
	$(PY) -m src.reporting.export_bi

roi:               ## Excel business case
	$(PY) -m src.evaluation.roi

alerts:
	$(PY) -m src.alerts.alerts

notebooks:
	cd notebooks && for n in *.ipynb; do ../.venv/bin/jupyter nbconvert --to notebook --execute --inplace $$n; done

test:
	$(PY) -m pytest -q

lint:
	.venv/bin/ruff check .
	.venv/bin/sqlfluff lint dbt_project/models dbt_project/tests

all:               ## full pipeline on sample data
	$(MAKE) sample
	$(MAKE) load SAMPLE=1
	$(MAKE) dbt
	$(MAKE) train
	$(MAKE) report
	$(MAKE) roi

clean:
	rm -rf warehouse dbt_project/target dbt_project/logs

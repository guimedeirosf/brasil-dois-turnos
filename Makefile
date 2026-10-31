# Atalhos locais e dos workflows. Requer uv, e Node 20+ para web/ e chat-worker/.
SHELL := /bin/bash
PY := .venv/bin/python
DBT := cd transform && ../.venv/bin/dbt
ANO ?= 2026
CARGO ?= presidente

# Modelos por fonte: cada workflow reconstroi so o que suas fontes alimentam
MODELOS_MACRO := +fct_macro_mes
EXCLUIR_DA_ELEICAO := stg_bcb__series fct_macro_mes

.PHONY: setup lint test fixtures dbt-ci gold-ci exemplos catalogo ingest-eleicao ingest-macro \
	ingest-anual dbt-eleicao dbt-macro exportar publicar web worker limpar

setup:
	uv venv --python 3.12 .venv
	uv pip install --python $(PY) -e "ingestion[dev,r2]" -e "models_ml[dev]" dbt-duckdb sqlfluff \
		sqlfluff-templater-dbt pre-commit
	$(DBT) deps --profiles-dir .
	.venv/bin/pre-commit install --hook-type pre-commit --hook-type commit-msg

lint:
	.venv/bin/ruff check ingestion models_ml scripts
	.venv/bin/ruff format --check ingestion models_ml scripts
	cd ingestion && ../.venv/bin/mypy src
	cd models_ml && ../.venv/bin/mypy src

test:
	cd ingestion && ../$(PY) -m pytest --cov=ingestion
	cd models_ml && ../$(PY) -m pytest --cov=models_ml

# --- Ambiente ci: Bronze e Gold a partir das fixtures versionadas ----------------------
fixtures:
	DATA_DIR=$(CURDIR)/data/ci $(PY) -m ingestion.fixtures

dbt-ci: fixtures
	cd transform && BRONZE_DIR=../data/ci/bronze ../.venv/bin/dbt build --profiles-dir . --target ci
	cd transform && BRONZE_DIR=../data/ci/bronze DBT_TARGET=ci ../.venv/bin/sqlfluff lint models tests

gold-ci: dbt-ci
	DATA_DIR=$(CURDIR)/data/ci $(PY) -m ingestion exportar-gold

exemplos: gold-ci
	$(PY) scripts/validar_exemplos.py --gold data/ci/gold
	$(PY) scripts/gerar_catalogo.py --gold data/ci/gold --verificar

catalogo:
	$(PY) scripts/gerar_catalogo.py --gold data/gold

# --- Cargas reais --------------------------------------------------------------------
ingest-eleicao:
	$(PY) -m ingestion tse --ano $(ANO) --cargo $(CARGO)
	$(PY) -m ingestion diretorios
	$(PY) -m ingestion sidra --tabela populacao_estimada

ingest-macro:
	$(PY) -m ingestion bcb --desde 1989-01

ingest-anual:
	$(PY) -m ingestion diretorios
	$(PY) -m ingestion sidra --tabela populacao_estimada
	$(PY) -m ingestion sidra --tabela pib_municipal

dbt-eleicao:
	$(DBT) build --profiles-dir . --exclude $(EXCLUIR_DA_ELEICAO)

dbt-macro:
	$(DBT) build --profiles-dir . --select $(MODELOS_MACRO)

exportar:
	$(PY) -m ingestion exportar-gold

publicar:
	$(PY) -m ingestion publicar-gold --run-id $${GITHUB_RUN_ID:-local}

# --- Front e chat --------------------------------------------------------------------
web:
	cd web && npm ci && npm run build

worker:
	cd chat-worker && npm ci && npm run build:semantic && npm run typecheck && npm test

limpar:
	rm -rf data/ci transform/target web/dist web/src/.observablehq/cache

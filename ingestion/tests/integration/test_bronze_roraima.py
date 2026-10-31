"""Fonte -> Bronze ponta a ponta com fixtures reais (recorte de Roraima, presidente 2026)."""

from __future__ import annotations

import duckdb
import pytest

from ingestion.config import Config
from ingestion.fixtures import carregar_fixtures

pytestmark = pytest.mark.integration


def test_fixtures_viram_bronze_consistente(cfg: Config) -> None:
    linhas = carregar_fixtures(cfg)

    assert linhas["votacao_secao"] > 1000
    assert linhas["detalhe_votacao_secao"] == 216  # 108 secoes x 2 turnos
    bronze = cfg.bronze_dir.as_posix()
    con = duckdb.connect()
    votos, comparecimento = con.execute(
        f"""
        with v as (
            select NR_TURNO, sum(QT_VOTOS::int) as votos
            from read_parquet('{bronze}/tse/votacao_secao/*/*/*/*.parquet') group by 1
        ), d as (
            select NR_TURNO, sum(QT_COMPARECIMENTO::int) as comparecimento
            from read_parquet('{bronze}/tse/detalhe_votacao_secao/*/*/*/*.parquet') group by 1
        )
        select sum(votos), sum(comparecimento) from v join d using (NR_TURNO)
        """
    ).fetchone()
    assert votos == comparecimento

    acentos = con.execute(
        f"select count(*) from read_parquet('{bronze}/tse/votacao_secao/*/*/*/*.parquet')"
        " where NM_VOTAVEL like '%Á%' or NM_MUNICIPIO like '%Ã%'"
    ).fetchone()
    assert acentos is not None and acentos[0] > 0  # latin-1 convertido sem perda


def test_carga_repetida_nao_duplica(cfg: Config) -> None:
    primeira = carregar_fixtures(cfg)
    segunda = carregar_fixtures(cfg)
    assert primeira == segunda
    padrao = f"{cfg.bronze_dir.as_posix()}/tse/votacao_secao/**/*.parquet"
    total = duckdb.connect().execute(f"select count(*) from read_parquet('{padrao}')").fetchone()
    assert total is not None and total[0] == primeira["votacao_secao"]

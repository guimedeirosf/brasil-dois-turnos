from __future__ import annotations

import json

import duckdb

from ingestion.config import Config
from ingestion.gold import exportar_gold


def test_exporta_particionado_e_gera_manifesto(cfg: Config) -> None:
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(cfg.warehouse)) as con:
        con.execute("create schema gold")
        con.execute(
            "create table gold.fct_x as select * from (values (2022, 'presidente', 1), "
            "(2026, 'presidente', 2), (2026, 'presidente', 3)) t(ano, cargo, v)"
        )
        con.execute("create table gold.dim_y as select 2026 as ano, 'presidente' as cargo, 1 as k")
        con.execute("create table gold.dim_eleicao as select 2026 as ano, 'presidente' as cargo")
        con.execute("create table gold.dim_z as select 1 as k")
        con.execute("create table gold.outra as select 1 as k")

    exportadas = exportar_gold(cfg)

    assert exportadas == ["dim_eleicao", "dim_y", "dim_z", "fct_x"]
    assert (cfg.gold_dir / "fct_x/ano=2026/cargo=presidente/part-0.parquet").exists()
    assert (cfg.gold_dir / "dim_y/ano=2026/cargo=presidente/part-0.parquet").exists()
    assert (cfg.gold_dir / "dim_eleicao/part-0.parquet").exists()
    assert (cfg.gold_dir / "dim_z/part-0.parquet").exists()
    manifesto = json.loads((cfg.gold_dir / "_manifest.json").read_text(encoding="utf-8"))
    assert manifesto["tabelas"]["fct_x"]["linhas"] == 3
    assert {a["particao"]["ano"] for a in manifesto["tabelas"]["fct_x"]["arquivos"]} == {
        "2022",
        "2026",
    }


def test_reexportar_substitui_particoes_antigas(cfg: Config) -> None:
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(cfg.warehouse)) as con:
        con.execute("create schema gold")
        con.execute("create table gold.srv_z as select 2022 as ano, 'presidente' as cargo, 1 as v")
    exportar_gold(cfg)
    with duckdb.connect(str(cfg.warehouse)) as con:
        con.execute(
            "create or replace table gold.srv_z"
            " as select 2026 as ano, 'presidente' as cargo, 1 as v"
        )
    exportar_gold(cfg)

    assert not (cfg.gold_dir / "srv_z/ano=2022").exists()
    assert (cfg.gold_dir / "srv_z/ano=2026").exists()

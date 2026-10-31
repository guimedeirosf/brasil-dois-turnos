"""Exportacao da Gold (schema `gold` do warehouse) para Parquet + _manifest.json."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from ingestion.config import Config
from ingestion.storage import sha256_arquivo

PREFIXOS_EXPORTADOS = ("dim_", "fct_", "srv_")
LINHAS_POR_ROW_GROUP = 100_000
# Vem inteira do seed eleicoes_catalogo, entao nao e particionada por eleicao
NAO_PARTICIONADAS = {"dim_eleicao"}


def exportar_gold(cfg: Config, schema: str = "gold") -> list[str]:
    """Grava cada tabela com ano e cargo em gold/<tabela>/ano=<ano>/cargo=<cargo>/part-0.parquet.

    As colunas ano e cargo ficam so no caminho (leitura com hive_partitioning). Assim cada
    workflow publica so as eleicoes que processou sem apagar as outras.
    Tabelas sem ano/cargo (municipios, partidos, macro) viram um arquivo unico.
    """
    cfg.gold_dir.mkdir(parents=True, exist_ok=True)
    exportadas = []
    with duckdb.connect(str(cfg.warehouse), read_only=True) as con:
        tabelas = [
            linha[0]
            for linha in con.execute(
                "select table_name from information_schema.tables where table_schema = ?"
                " order by 1",
                [schema],
            ).fetchall()
            if linha[0].startswith(PREFIXOS_EXPORTADOS)
        ]
        for tabela in tabelas:
            colunas = {
                linha[0]
                for linha in con.execute(
                    "select column_name from information_schema.columns"
                    " where table_schema = ? and table_name = ?",
                    [schema, tabela],
                ).fetchall()
            }
            destino = cfg.gold_dir / tabela
            if destino.exists():
                shutil.rmtree(destino)
            opcoes = f"format parquet, compression zstd, row_group_size {LINHAS_POR_ROW_GROUP}"
            if tabela not in NAO_PARTICIONADAS and {"ano", "cargo"} <= colunas:
                con.execute(
                    f"copy (select * from {schema}.{tabela} order by all) to '{destino.as_posix()}'"
                    f" ({opcoes}, partition_by (ano, cargo), filename_pattern 'part-{{i}}')"
                )
            else:
                destino.mkdir(parents=True)
                con.execute(
                    f"copy (select * from {schema}.{tabela} order by all)"
                    f" to '{(destino / 'part-0.parquet').as_posix()}' ({opcoes})"
                )
            exportadas.append(tabela)
    gerar_manifesto(cfg.gold_dir)
    return exportadas


def gerar_manifesto(gold_dir: Path) -> dict[str, Any]:
    """Lista tabelas, particoes, linhas e hash de tudo que existe em gold/."""
    tabelas: dict[str, Any] = {}
    con = duckdb.connect()
    for arquivo in sorted(gold_dir.rglob("*.parquet")):
        relativo = arquivo.relative_to(gold_dir)
        if relativo.parts[0].startswith("_"):
            continue
        tabela = relativo.parts[0]
        particao = dict(p.split("=", 1) for p in relativo.parts[1:-1])
        linhas = con.execute(
            "select count(*) from read_parquet(?)", [arquivo.as_posix()]
        ).fetchone()
        entrada = tabelas.setdefault(tabela, {"linhas": 0, "arquivos": []})
        entrada["linhas"] += linhas[0] if linhas else 0
        entrada["arquivos"].append(
            {
                "caminho": relativo.as_posix(),
                "particao": particao,
                "linhas": linhas[0] if linhas else 0,
                "bytes": arquivo.stat().st_size,
                "sha256": sha256_arquivo(arquivo),
            }
        )
    con.close()
    manifesto = {"gerado_em": datetime.now(UTC).isoformat(timespec="seconds"), "tabelas": tabelas}
    (gold_dir / "_manifest.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifesto

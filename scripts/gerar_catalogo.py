"""Sincroniza semantic/catalog.yml com a Gold e com as descricoes do dbt.

Mantem o que e escrito a mao (descricao da tabela, sinonimos, valores validos) e atualiza
colunas e tipos a partir dos Parquet da Gold. Descricoes de coluna vazias sao preenchidas
com as do schema.yml do dbt (target/manifest.json).

    python scripts/gerar_catalogo.py --gold data/gold            # atualiza
    python scripts/gerar_catalogo.py --gold data/ci/gold --verificar   # CI: falha se divergir
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb
import yaml

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / "semantic" / "catalog.yml"
MANIFESTO_DBT = RAIZ / "transform" / "target" / "manifest.json"


def colunas_da_gold(gold: Path, tabela: str) -> dict[str, str] | None:
    arquivos = sorted((gold / tabela).rglob("*.parquet"))
    if not arquivos:
        return None
    lista = ", ".join(f"'{a.as_posix()}'" for a in arquivos)
    linhas = duckdb.sql(
        f"describe select * from read_parquet([{lista}], hive_partitioning = true)"
    ).fetchall()
    return {nome: tipo for nome, tipo, *_ in linhas}


def descricoes_dbt() -> dict[str, dict[str, str]]:
    if not MANIFESTO_DBT.exists():
        return {}
    manifesto = json.loads(MANIFESTO_DBT.read_text(encoding="utf-8"))
    return {
        no["name"]: {c: v.get("description", "") for c, v in no.get("columns", {}).items()}
        for no in manifesto["nodes"].values()
        if no["resource_type"] == "model"
    }


def sincronizar(catalogo: dict[str, Any], gold: Path) -> list[str]:
    mudancas = []
    dbt = descricoes_dbt()
    for nome, tabela in catalogo["tabelas"].items():
        reais = colunas_da_gold(gold, nome)
        if reais is None:
            continue  # tabela ainda nao gerada neste ambiente (ex.: inferencia no CI)
        atuais: dict[str, Any] = tabela.setdefault("colunas", {}) or {}
        for coluna in list(atuais):
            if coluna not in reais:
                mudancas.append(f"{nome}.{coluna}: removida")
                del atuais[coluna]
        for coluna, tipo in reais.items():
            info = atuais.setdefault(coluna, {})
            if info.get("tipo") != tipo:
                mudancas.append(f"{nome}.{coluna}: tipo {info.get('tipo')} -> {tipo}")
                info["tipo"] = tipo
            if not info.get("descricao") and dbt.get(nome, {}).get(coluna):
                info["descricao"] = dbt[nome][coluna]
        tabela["colunas"] = atuais
    return mudancas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=RAIZ / "data" / "gold")
    parser.add_argument("--verificar", action="store_true")
    args = parser.parse_args()

    catalogo = yaml.safe_load(CATALOGO.read_text(encoding="utf-8"))
    mudancas = sincronizar(catalogo, args.gold)
    for m in mudancas:
        print(m)
    if args.verificar:
        return 1 if mudancas else 0
    CATALOGO.write_text(
        yaml.safe_dump(catalogo, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Executa todo SQL de semantic/examples.yml no DuckDB contra a Gold de teste.

Cada tabela do catalogo vira uma view sobre os Parquet da Gold (como no navegador). Tabela que
ainda nao existe no ambiente (ex.: fct_transicao_estimada no CI) vira uma view vazia com os
tipos do catalogo, para que o SQL seja ao menos compilado e executado.

    python scripts/validar_exemplos.py --gold data/ci/gold
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import yaml

RAIZ = Path(__file__).resolve().parents[1]


def conectar(gold: Path, catalogo: dict) -> duckdb.DuckDBPyConnection:  # type: ignore[type-arg]
    con = duckdb.connect()
    for tabela, spec in catalogo["tabelas"].items():
        arquivos = sorted((gold / tabela).rglob("*.parquet"))
        if arquivos:
            lista = ", ".join(f"'{a.as_posix()}'" for a in arquivos)
            con.execute(
                f"create view {tabela} as select * from read_parquet([{lista}],"
                " hive_partitioning = true, union_by_name = true)"
            )
        else:
            colunas = ", ".join(
                f"cast(null as {c.get('tipo', 'VARCHAR')}) as {nome}"
                for nome, c in spec["colunas"].items()
            )
            con.execute(f"create view {tabela} as select {colunas} where false")
    return con


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=RAIZ / "data" / "ci" / "gold")
    args = parser.parse_args()

    catalogo = yaml.safe_load((RAIZ / "semantic" / "catalog.yml").read_text(encoding="utf-8"))
    exemplos = yaml.safe_load((RAIZ / "semantic" / "examples.yml").read_text(encoding="utf-8"))
    con = conectar(args.gold, catalogo)
    falhas = 0
    for exemplo in exemplos["exemplos"]:
        try:
            con.execute(exemplo["sql"]).fetchall()
        except duckdb.Error as erro:
            falhas += 1
            print(f"FALHA: {exemplo['pergunta']}\n  {erro}")
    print(f"{len(exemplos['exemplos']) - falhas}/{len(exemplos['exemplos'])} exemplos ok")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())

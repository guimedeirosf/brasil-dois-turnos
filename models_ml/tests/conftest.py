from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from models_ml.matrices import COLUNA_POR_CATEGORIA, DESTINOS, ORIGENS
from models_ml.validate import gerar_secoes, matriz_plausivel


def secoes_sinteticas(n: int = 120, uf: str = "RR", semente: int = 3) -> pl.DataFrame:
    """fct_secao_resumo sintetico (dois turnos) gerado a partir da matriz plausivel."""
    origem, destino, aptos = gerar_secoes(matriz_plausivel(), n_secoes=n, semente=semente)
    base = {
        "uf": [uf] * n,
        "cod_municipio_tse": (np.arange(n) // 10 + 1000).tolist(),
        "zona": (np.arange(n) % 3 + 1).tolist(),
        "secao": np.arange(n).tolist(),
        "aptos": origem.sum(axis=1).astype(int).tolist(),
    }
    t1 = pl.DataFrame(
        {
            **base,
            "turno": [1] * n,
            **{COLUNA_POR_CATEGORIA[c]: origem[:, i].astype(int) for i, c in enumerate(ORIGENS)},
        }
    )
    zeros = {COLUNA_POR_CATEGORIA[c]: [0] * n for c in ("ESQ", "CENTRO", "DIR")}
    t2 = pl.DataFrame(
        {
            **base,
            "turno": [2] * n,
            **zeros,
            **{COLUNA_POR_CATEGORIA[c]: destino[:, j].astype(int) for j, c in enumerate(DESTINOS)},
        }
    ).select(t1.columns)
    assert (aptos > 0).all()
    return pl.concat([t1, t2])


@pytest.fixture
def secoes() -> pl.DataFrame:
    return secoes_sinteticas()


@pytest.fixture
def gold_sintetica(tmp_path: Path, secoes: pl.DataFrame) -> Path:
    destino = tmp_path / "gold" / "fct_secao_resumo" / "ano=2026" / "cargo=presidente"
    destino.mkdir(parents=True)
    secoes.write_parquet(destino / "part-0.parquet")
    return tmp_path / "gold"

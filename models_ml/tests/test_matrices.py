from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from models_ml.matrices import (
    DescarteExcessivo,
    ler_secoes,
    montar_matrizes,
    parear_secoes,
    verificar_descarte,
)


def test_pareamento_sem_descartes(secoes: pl.DataFrame) -> None:
    pareadas, auditoria = parear_secoes(secoes, "RR")
    assert pareadas.height == 120
    assert auditoria.secoes_pareadas == 120
    assert auditoria.pct_aptos_descartados == 0
    verificar_descarte(auditoria)


def test_descarta_sem_par_poucos_aptos_e_variacao(secoes: pl.DataFrame) -> None:
    t1 = secoes.filter(pl.col("turno") == 1)
    t2 = secoes.filter(pl.col("turno") == 2)
    t2 = t2.filter(pl.col("secao") != 0)  # secao 0 sem par
    t2 = t2.with_columns(
        aptos=pl.when(pl.col("secao") == 1).then(pl.col("aptos") * 2).otherwise(pl.col("aptos"))
    )
    t1 = t1.with_columns(aptos=pl.when(pl.col("secao") == 2).then(30).otherwise(pl.col("aptos")))

    pareadas, auditoria = parear_secoes(pl.concat([t1, t2]), "RR")

    assert auditoria.secoes_sem_par == 1
    assert auditoria.secoes_variacao_aptos == 1
    assert auditoria.secoes_poucos_aptos == 1
    assert pareadas.height == 117


def test_descarte_acima_de_5_porcento_falha(secoes: pl.DataFrame) -> None:
    sem_segundo_turno = secoes.filter((pl.col("turno") == 1) | (pl.col("secao") >= 20))
    _, auditoria = parear_secoes(sem_segundo_turno, "RR")
    with pytest.raises(DescarteExcessivo, match="RR"):
        verificar_descarte(auditoria)


def test_matrizes_somam_um(secoes: pl.DataFrame) -> None:
    pareadas, _ = parear_secoes(secoes, "RR")
    m = montar_matrizes(pareadas)
    assert m.x.shape == (120, 8)
    assert m.t.shape == (120, 5)
    np.testing.assert_allclose(m.x.sum(axis=1), 1)
    np.testing.assert_allclose(m.t.sum(axis=1), 1)
    np.testing.assert_array_equal(m.n, m.contagens_origem.sum(axis=1))


def test_ler_secoes_filtra_uf(gold_sintetica: Path) -> None:
    lidas = ler_secoes(str(gold_sintetica), 2026, "presidente", "RR")
    assert lidas.height == 240
    assert ler_secoes(str(gold_sintetica), 2026, "presidente", "SP").height == 0

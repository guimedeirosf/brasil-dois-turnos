from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from models_ml import cli
from models_ml.ecological import (
    ConfigAmostragem,
    ResultadoEI,
    amostras_para_tabela,
    combinar,
    resumir,
    tabela_para_amostras,
)
from models_ml.matrices import Matrizes, montar_matrizes, parear_secoes
from models_ml.validate import matriz_plausivel


def _amostras_em_torno(matriz: np.ndarray, s: int = 200, semente: int = 0) -> np.ndarray:
    rng = np.random.default_rng(semente)
    return np.stack([[rng.dirichlet(linha * 2000 + 1e-3) for linha in matriz] for _ in range(s)])


def test_combinar_pondera_por_eleitores_da_origem() -> None:
    a = np.zeros((10, 8, 5))
    a[:, :, 0] = 1
    b = np.zeros((10, 8, 5))
    b[:, :, 1] = 1
    pesos_a = np.full(8, 300.0)
    pesos_b = np.full(8, 100.0)
    pesos_b[3] = 0  # origem sem eleitores no grupo b
    b[:, 3, :] = np.nan

    r = combinar([ResultadoEI(a, pesos_a, 1.001, 900), ResultadoEI(b, pesos_b, 1.004, 500)])

    np.testing.assert_allclose(r.amostras[0, 0, :2], [0.75, 0.25])
    np.testing.assert_allclose(r.amostras[0, 3, :2], [1.0, 0.0])
    assert r.rhat_max == 1.004
    assert r.ess_min == 500


def test_resumo_tem_intervalo_e_votos() -> None:
    amostras = _amostras_em_torno(matriz_plausivel())
    pesos = np.array([300.0, 280, 40, 30, 50, 10, 20, 0])
    resumo = resumir(ResultadoEI(amostras, pesos, 1.0, 1000), "RR", ConfigAmostragem(), "aprovado")

    assert resumo.height == 7 * 5  # origem sem eleitores fica de fora
    assert (resumo["ic_inferior"] <= resumo["pct_estimado"]).all()
    assert (resumo["pct_estimado"] <= resumo["ic_superior"]).all()
    a_a = resumo.filter((pl.col("origem") == "CAND_A") & (pl.col("destino") == "CAND_A"))
    assert a_a["votos_estimados"].item() == pytest.approx(300 * a_a["pct_estimado"].item())


def test_ida_e_volta_formato_longo() -> None:
    amostras = _amostras_em_torno(matriz_plausivel(), s=7)
    original = ResultadoEI(amostras, np.ones(8), 1.0, 1.0)
    volta = tabela_para_amostras(amostras_para_tabela(original, "RR"), np.ones(8), 1.0, 1.0)
    np.testing.assert_array_equal(volta.amostras, amostras)


def _ajuste_falso(m: Matrizes, cfg: ConfigAmostragem) -> ResultadoEI:
    return ResultadoEI(
        _amostras_em_torno(matriz_plausivel(), s=100), m.contagens_origem.sum(axis=0), 1.002, 800
    )


def test_cli_inferir_e_agregar(
    gold_sintetica: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "ajustar", _ajuste_falso)
    parciais = tmp_path / "parciais"
    comum = ["--ano", "2026", "--cargo", "presidente"]

    assert cli.main(["inferir", *comum, "--uf", "RR", "--entrada", str(gold_sintetica),
                     "--saida", str(parciais), "--max-secoes", "50"]) == 0  # fmt: skip
    assert (parciais / "amostras_RR.parquet").exists()

    codigo = cli.main(
        ["agregar", *comum, "--parciais", str(parciais), "--gold", str(gold_sintetica)]
    )
    assert codigo == 0
    transicao = pl.read_parquet(
        gold_sintetica / "fct_transicao_estimada/ano=2026/cargo=presidente/part-0.parquet"
    )
    assert set(transicao["abrangencia"]) == {"RR", "BR"}
    assert set(transicao["status_validacao"]) == {"aprovado"}
    auditoria = pl.read_parquet(
        gold_sintetica / "fct_inferencia_auditoria/ano=2026/cargo=presidente/part-0.parquet"
    )
    assert auditoria["secoes_pareadas"].item() == 120


def test_agregar_reprovado_bloqueia(
    gold_sintetica: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def ajuste_ruim(m: Matrizes, cfg: ConfigAmostragem) -> ResultadoEI:
        r = _ajuste_falso(m, cfg)
        return ResultadoEI(r.amostras, r.pesos, 1.2, r.ess_min)  # R-hat ruim

    monkeypatch.setattr(cli, "ajustar", ajuste_ruim)
    parciais = tmp_path / "parciais"
    comum = ["--ano", "2026", "--cargo", "presidente"]
    cli.main(["inferir", *comum, "--uf", "RR", "--entrada", str(gold_sintetica),
              "--saida", str(parciais)])  # fmt: skip
    assert cli.main(["agregar", *comum, "--parciais", str(parciais), "--gold", str(tmp_path)]) == 2


@pytest.mark.lento
def test_pyei_recupera_matriz_sintetica() -> None:
    """Recuperacao de matriz conhecida com o PyEI de verdade (minutos; roda no workflow)."""
    pytest.importorskip("pyei")
    from conftest import secoes_sinteticas

    from models_ml.ecological import ajustar

    pareadas, _ = parear_secoes(secoes_sinteticas(n=300, semente=11), "SINT")
    cfg = ConfigAmostragem(cadeias=2, aquecimento=500, amostras=500)
    r = ajustar(montar_matrizes(pareadas), cfg)

    verdadeira = matriz_plausivel()
    inferior = np.nanpercentile(r.amostras, 2.5, axis=0)
    superior = np.nanpercentile(r.amostras, 97.5, axis=0)
    dentro = (inferior <= verdadeira) & (verdadeira <= superior)
    # As linhas grandes (finalistas e abstencao) precisam ser recuperadas
    for linha in (0, 1, 7):
        assert dentro[linha].mean() >= 0.8, (linha, inferior[linha], superior[linha])
    assert r.rhat_max < 1.05

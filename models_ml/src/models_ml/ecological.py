"""Inferencia ecologica R x C (PyEI, multinomial-Dirichlet) e agregacao das amostras.

Resultado de cada ajuste: amostras posteriores da matriz de transicao do distrito
(amostras x 8 origens x 5 destinos). A agregacao (grupos -> UF -> Brasil) e feita amostra a
amostra, ponderando cada linha pelo total de eleitores daquela origem, para que os intervalos
de credibilidade se propaguem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import numpy.typing as npt
import polars as pl

from models_ml.matrices import DESTINOS, ORIGENS, Matrizes

METODO = "pyei_multinomial_dirichlet"


@dataclass(frozen=True)
class ConfigAmostragem:
    cadeias: int = 4
    aquecimento: int = 2000
    amostras: int = 2000
    semente: int = 20261025
    target_accept: float = 0.99


@dataclass(frozen=True)
class ResultadoEI:
    amostras: npt.NDArray[np.float64]  # S x 8 x 5; linhas sem eleitores ficam NaN
    pesos: npt.NDArray[np.float64]  # 8, eleitores por origem
    rhat_max: float
    ess_min: float


def ajustar(m: Matrizes, cfg: ConfigAmostragem) -> ResultadoEI:
    """Roda o PyEI num conjunto de secoes. Origens sem nenhum eleitor ficam de fora do modelo."""
    import arviz as az
    from pyei.r_by_c import RowByColumnEI

    pesos = m.contagens_origem.sum(axis=0)
    ativas = np.flatnonzero(pesos > 0)
    x = m.x[:, ativas]
    x = x / x.sum(axis=1, keepdims=True)

    ei = RowByColumnEI(model_name="multinomial-dirichlet")
    ei.fit(
        x.T,
        m.t.T,
        m.n,
        demographic_group_names=[ORIGENS[i] for i in ativas],
        candidate_names=list(DESTINOS),
        chains=cfg.cadeias,
        tune=cfg.aquecimento,
        draws=cfg.amostras,
        target_accept=cfg.target_accept,
        random_seed=cfg.semente,
        progressbar=False,
    )
    parciais = np.asarray(ei.sampled_voting_prefs, dtype=float)  # S x ativas x 5
    amostras = np.full((parciais.shape[0], len(ORIGENS), len(DESTINOS)), np.nan)
    amostras[:, ativas, :] = parciais

    rhat = az.rhat(ei.sim_trace)
    ess = az.ess(ei.sim_trace)
    rhat_max = float(max(np.nanmax(rhat[v].values) for v in rhat.data_vars))
    ess_min = float(min(np.nanmin(ess[v].values) for v in ess.data_vars))
    return ResultadoEI(amostras, pesos, rhat_max, ess_min)


def combinar(resultados: list[ResultadoEI]) -> ResultadoEI:
    """Media ponderada, amostra a amostra, das matrizes de varios grupos ou UFs."""
    total_amostras = min(r.amostras.shape[0] for r in resultados)
    soma = np.zeros((total_amostras, len(ORIGENS), len(DESTINOS)))
    pesos = np.zeros(len(ORIGENS))
    for r in resultados:
        contribui = r.pesos > 0
        soma[:, contribui, :] += (
            r.amostras[:total_amostras, contribui, :] * r.pesos[None, contribui, None]
        )
        pesos += r.pesos
    with np.errstate(invalid="ignore", divide="ignore"):
        amostras = soma / pesos[None, :, None]
    amostras[:, pesos == 0, :] = np.nan
    return ResultadoEI(
        amostras=amostras,
        pesos=pesos,
        rhat_max=max(r.rhat_max for r in resultados),
        ess_min=min(r.ess_min for r in resultados),
    )


def resumir(
    resultado: ResultadoEI, abrangencia: str, cfg: ConfigAmostragem, status: str
) -> pl.DataFrame:
    """Uma linha por origem x destino: media posterior, IC 95% e votos estimados."""
    media = np.nanmean(resultado.amostras, axis=0)
    inferior = np.nanpercentile(resultado.amostras, 2.5, axis=0)
    superior = np.nanpercentile(resultado.amostras, 97.5, axis=0)
    executado_em = datetime.now(UTC).replace(microsecond=0)
    linhas = []
    for i, origem in enumerate(ORIGENS):
        if resultado.pesos[i] == 0:
            continue
        for j, destino in enumerate(DESTINOS):
            linhas.append(
                {
                    "abrangencia": abrangencia,
                    "origem": origem,
                    "destino": destino,
                    "pct_estimado": float(media[i, j]),
                    "ic_inferior": float(inferior[i, j]),
                    "ic_superior": float(superior[i, j]),
                    "votos_estimados": float(media[i, j] * resultado.pesos[i]),
                    "eleitores_origem": float(resultado.pesos[i]),
                    "metodo": METODO,
                    "semente": cfg.semente,
                    "rhat_max": resultado.rhat_max,
                    "ess_min": resultado.ess_min,
                    "status_validacao": status,
                    "executado_em": executado_em,
                }
            )
    return pl.DataFrame(linhas)


def amostras_para_tabela(resultado: ResultadoEI, abrangencia: str) -> pl.DataFrame:
    """Formato longo para gravar o parcial de cada UF (agregado depois para o Brasil)."""
    s, r, c = resultado.amostras.shape
    return pl.DataFrame(
        {
            "abrangencia": [abrangencia] * (s * r * c),
            "amostra": np.repeat(np.arange(s), r * c),
            "origem": np.tile(np.repeat(np.arange(r), c), s),
            "destino": np.tile(np.arange(c), s * r),
            "valor": resultado.amostras.reshape(-1),
        }
    )


def tabela_para_amostras(
    tabela: pl.DataFrame, pesos: npt.NDArray[np.float64], rhat_max: float, ess_min: float
) -> ResultadoEI:
    s = tabela["amostra"].n_unique()
    ordenada = tabela.sort(["amostra", "origem", "destino"])
    amostras = ordenada["valor"].to_numpy().reshape(s, len(ORIGENS), len(DESTINOS))
    return ResultadoEI(amostras, pesos, rhat_max, ess_min)

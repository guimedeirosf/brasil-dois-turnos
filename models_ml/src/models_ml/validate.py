"""Validacoes que bloqueiam a publicacao da matriz de transicao, e dados sinteticos.

Bloqueiam: R-hat >= 1,01; linha que nao soma 1 (tolerancia 0,001); reconstrucao do 2o turno
com erro >= 0,5 ponto percentual. Fidelidade CAND_A->CAND_A ou CAND_B->CAND_B abaixo de 0,85
nao bloqueia: manda a execucao para revisao manual.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from models_ml.matrices import DESTINOS, ORIGENS

RHAT_MAX = 1.01
TOLERANCIA_SOMA = 0.001
ERRO_RECONSTRUCAO_PP = 0.5
FIDELIDADE_MIN = 0.85

APROVADO = "aprovado"
REVISAO = "revisao_manual"
REPROVADO = "reprovado"


@dataclass
class Relatorio:
    abrangencia: str
    erros: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.erros:
            return REPROVADO
        return REVISAO if self.alertas else APROVADO


def validar(
    abrangencia: str,
    media: npt.NDArray[np.float64],
    rhat_max: float,
    origem_total: npt.NDArray[np.float64],
    destino_total: npt.NDArray[np.float64],
) -> Relatorio:
    """`media` e 8 x 5; os totais sao em eleitores (aptos) na abrangencia."""
    rel = Relatorio(abrangencia)
    if not rhat_max < RHAT_MAX:
        rel.erros.append(f"R-hat maximo {rhat_max:.4f} >= {RHAT_MAX}")

    ativas = origem_total > 0
    somas = media[ativas].sum(axis=1)
    if np.any(np.abs(somas - 1) > TOLERANCIA_SOMA):
        rel.erros.append(f"linhas nao somam 1: {np.round(somas, 4).tolist()}")

    erro_pp = erro_reconstrucao_pp(media, origem_total, destino_total)
    if erro_pp >= ERRO_RECONSTRUCAO_PP:
        rel.erros.append(f"reconstrucao do 2o turno com erro de {erro_pp:.2f} p.p.")

    for categoria in ("CAND_A", "CAND_B"):
        i, j = ORIGENS.index(categoria), DESTINOS.index(categoria)
        if media[i, j] <= FIDELIDADE_MIN:
            rel.alertas.append(f"fidelidade {categoria} {media[i, j]:.3f} <= {FIDELIDADE_MIN}")
    return rel


def erro_reconstrucao_pp(
    media: npt.NDArray[np.float64],
    origem_total: npt.NDArray[np.float64],
    destino_total: npt.NDArray[np.float64],
) -> float:
    """Maior diferenca, em pontos percentuais, entre X . matriz e o 2o turno observado."""
    ativas = origem_total > 0
    x = origem_total[ativas] / origem_total.sum()
    previsto = x @ media[ativas]
    observado = destino_total / destino_total.sum()
    return float(np.max(np.abs(previsto - observado)) * 100)


def intervalos_contem_media(
    media: npt.NDArray[np.float64],
    inferior: npt.NDArray[np.float64],
    superior: npt.NDArray[np.float64],
) -> bool:
    ok = (inferior <= media) & (media <= superior)
    return bool(np.all(ok | np.isnan(media)))


# --- Dados sinteticos ----------------------------------------------------------------


def matriz_plausivel() -> npt.NDArray[np.float64]:
    """Matriz 8 x 5 de referencia para testes (linhas somam 1)."""
    return np.array(
        [
            [0.93, 0.02, 0.01, 0.01, 0.03],  # CAND_A
            [0.02, 0.92, 0.01, 0.02, 0.03],  # CAND_B
            [0.70, 0.10, 0.05, 0.08, 0.07],  # ESQ
            [0.35, 0.35, 0.10, 0.10, 0.10],  # CENTRO
            [0.10, 0.70, 0.05, 0.08, 0.07],  # DIR
            [0.20, 0.20, 0.40, 0.10, 0.10],  # BRANCO
            [0.15, 0.15, 0.10, 0.45, 0.15],  # NULO
            [0.04, 0.04, 0.01, 0.01, 0.90],  # ABST
        ]
    )


def gerar_secoes(
    matriz: npt.NDArray[np.float64],
    n_secoes: int = 400,
    semente: int = 7,
    concentracao: float = 200.0,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.int64]]:
    """Gera contagens de origem e destino por secao a partir de uma matriz conhecida.

    Cada secao tem sua propria matriz (Dirichlet em torno da verdadeira), como no modelo.
    Devolve (contagens_origem n x 8, contagens_destino n x 5, aptos n).
    """
    rng = np.random.default_rng(semente)
    aptos = rng.integers(150, 450, size=n_secoes)
    perfil = np.array([0.30, 0.28, 0.04, 0.03, 0.05, 0.01, 0.02, 0.27])
    origem = np.zeros((n_secoes, len(ORIGENS)))
    destino = np.zeros((n_secoes, len(DESTINOS)))
    for s in range(n_secoes):
        x = rng.dirichlet(perfil * 60)
        origem[s] = rng.multinomial(aptos[s], x)
        for r in range(len(ORIGENS)):
            if origem[s, r] == 0:
                continue
            linha = rng.dirichlet(matriz[r] * concentracao + 1e-3)
            destino[s] += rng.multinomial(int(origem[s, r]), linha)
    return origem, destino, aptos.astype(np.int64)

from __future__ import annotations

import numpy as np

from models_ml.validate import (
    APROVADO,
    REPROVADO,
    REVISAO,
    erro_reconstrucao_pp,
    gerar_secoes,
    intervalos_contem_media,
    matriz_plausivel,
    validar,
)


def _totais(matriz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    origem = np.array([300.0, 280, 40, 30, 50, 10, 20, 270])
    return origem, origem @ matriz


def test_matriz_correta_aprovada() -> None:
    m = matriz_plausivel()
    origem, destino = _totais(m)
    rel = validar("BR", m, 1.003, origem, destino)
    assert rel.status == APROVADO, rel


def test_rhat_alto_reprova() -> None:
    m = matriz_plausivel()
    origem, destino = _totais(m)
    rel = validar("BR", m, 1.05, origem, destino)
    assert rel.status == REPROVADO
    assert "R-hat" in rel.erros[0]


def test_linha_que_nao_soma_um_reprova() -> None:
    m = matriz_plausivel().copy()
    origem, destino = _totais(m)
    m[2, 0] += 0.01
    assert validar("BR", m, 1.0, origem, destino).status == REPROVADO


def test_origem_sem_eleitores_e_ignorada() -> None:
    m = matriz_plausivel().copy()
    origem, _ = _totais(m)
    origem[3] = 0
    m[3] = np.nan
    destino = origem @ np.nan_to_num(m)
    assert validar("BR", m, 1.0, origem, destino).status == APROVADO


def test_reconstrucao_ruim_reprova() -> None:
    m = matriz_plausivel()
    origem, destino = _totais(m)
    destino = destino.copy()
    destino[0] += 0.02 * destino.sum()
    assert erro_reconstrucao_pp(m, origem, destino) > 0.5
    assert validar("BR", m, 1.0, origem, destino).status == REPROVADO


def test_fidelidade_baixa_vai_para_revisao() -> None:
    m = matriz_plausivel().copy()
    m[0] = [0.80, 0.10, 0.02, 0.03, 0.05]
    origem, destino = _totais(m)
    rel = validar("BR", m, 1.0, origem, destino)
    assert rel.status == REVISAO
    assert "CAND_A" in rel.alertas[0]


def test_intervalos() -> None:
    media = np.array([[0.5, np.nan]])
    assert intervalos_contem_media(media, np.array([[0.4, 0.0]]), np.array([[0.6, 1.0]]))
    assert not intervalos_contem_media(media, np.array([[0.55, 0]]), np.array([[0.6, 1]]))


def test_sinteticos_consistentes() -> None:
    origem, destino, aptos = gerar_secoes(matriz_plausivel(), n_secoes=50, semente=1)
    np.testing.assert_array_equal(origem.sum(axis=1), aptos)
    np.testing.assert_array_equal(destino.sum(axis=1), aptos)
    # Com a matriz verdadeira, a reconstrucao agregada fica muito proxima
    assert erro_reconstrucao_pp(matriz_plausivel(), origem.sum(0), destino.sum(0)) < 0.5

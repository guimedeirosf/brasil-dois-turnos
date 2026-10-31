from __future__ import annotations

import numpy as np

from models_ml.clustering import agrupar


def test_uf_pequena_fica_num_grupo_so() -> None:
    municipios = np.array([1, 1, 2, 3])
    assert agrupar(municipios, np.ones(4, dtype=np.int64), max_secoes=10).tolist() == [0, 0, 0, 0]


def test_municipio_inteiro_no_mesmo_grupo_e_grupos_equilibrados() -> None:
    municipios = np.repeat(np.arange(20), 50)  # 20 municipios de 50 secoes
    zonas = np.ones_like(municipios)
    grupos = agrupar(municipios, zonas, max_secoes=300)

    for mun in range(20):
        assert len(np.unique(grupos[municipios == mun])) == 1
    _, tamanhos = np.unique(grupos, return_counts=True)
    assert len(tamanhos) == 4
    assert tamanhos.max() <= 300


def test_municipio_grande_divide_por_zona() -> None:
    municipios = np.concatenate([np.zeros(600, dtype=np.int64), np.ones(100, dtype=np.int64)])
    zonas = np.concatenate([np.repeat(np.arange(6), 100), np.zeros(100, dtype=np.int64)])
    grupos = agrupar(municipios, zonas, max_secoes=400)

    assert len(np.unique(grupos[municipios == 0])) > 1
    for zona in range(6):
        assert len(np.unique(grupos[(municipios == 0) & (zonas == zona)])) == 1


def test_deterministico() -> None:
    municipios = np.repeat(np.arange(30), 40)
    zonas = np.ones_like(municipios)
    np.testing.assert_array_equal(
        agrupar(municipios, zonas, max_secoes=200), agrupar(municipios, zonas, max_secoes=200)
    )

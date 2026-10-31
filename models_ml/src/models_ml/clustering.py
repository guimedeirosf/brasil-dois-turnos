"""Divide uma UF grande em grupos de municipios para caber no limite de tempo do Actions.

Municipios inteiros vao para o mesmo grupo; municipio maior que o limite e dividido por zona.
Empacotamento guloso (maior primeiro, no grupo mais vazio), deterministico.
"""

from __future__ import annotations

import heapq

import numpy as np
import numpy.typing as npt

SECOES_POR_GRUPO = 1500


def agrupar(
    municipios: npt.NDArray[np.int64],
    zonas: npt.NDArray[np.int64],
    max_secoes: int = SECOES_POR_GRUPO,
) -> npt.NDArray[np.int64]:
    """Devolve o numero do grupo de cada secao."""
    total = len(municipios)
    if total <= max_secoes:
        return np.zeros(total, dtype=np.int64)

    # Unidades indivisiveis: municipio, ou (municipio, zona) quando o municipio e grande
    unidades: dict[tuple[int, int], list[int]] = {}
    tamanho_municipio = dict(zip(*np.unique(municipios, return_counts=True), strict=True))
    for i, (mun, zona) in enumerate(zip(municipios.tolist(), zonas.tolist(), strict=True)):
        chave = (mun, zona) if tamanho_municipio[mun] > max_secoes else (mun, -1)
        unidades.setdefault(chave, []).append(i)

    n_grupos = int(np.ceil(total / max_secoes))
    grupos: list[tuple[int, int]] = [(0, g) for g in range(n_grupos)]
    heapq.heapify(grupos)
    resultado = np.empty(total, dtype=np.int64)
    for chave in sorted(unidades, key=lambda k: (-len(unidades[k]), k)):
        ocupacao, grupo = heapq.heappop(grupos)
        resultado[unidades[chave]] = grupo
        heapq.heappush(grupos, (ocupacao + len(unidades[chave]), grupo))
    return resultado

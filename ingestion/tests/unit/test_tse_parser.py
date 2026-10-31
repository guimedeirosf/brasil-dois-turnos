from __future__ import annotations

import io
from pathlib import Path

import pytest

from ingestion.config import TSE_COLUNAS_LEGADO
from ingestion.sources.tse import detectar_layout, dividir_por_uf, ler_csv_uf

CABECALHO = '"ANO_ELEICAO";"NR_TURNO";"SG_UF";"NM_MUNICIPIO";"QT_VOTOS"\r\n'


def test_layout_com_cabecalho() -> None:
    colunas, tem_cabecalho = detectar_layout(CABECALHO, "votacao_secao")
    assert tem_cabecalho
    assert colunas == ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "NM_MUNICIPIO", "QT_VOTOS"]


def test_layout_legado_sem_cabecalho() -> None:
    legado = TSE_COLUNAS_LEGADO["votacao_secao"]
    linha = ";".join(f'"{i}"' for i in range(len(legado)))
    colunas, tem_cabecalho = detectar_layout(linha, "votacao_secao")
    assert not tem_cabecalho
    assert colunas == list(legado)


def test_layout_desconhecido_falha() -> None:
    with pytest.raises(ValueError, match="layout desconhecido"):
        detectar_layout('"a";"b"', "votacao_secao")


def test_divide_por_uf_e_converte_latin1(tmp_path: Path) -> None:
    corpo = (
        CABECALHO
        + '2026;1;"RR";"RORAINÓPOLIS";10\r\n'
        + '2026;1;"AP";"MACAPÁ";5\r\n'
        + '2026;2;"RR";"CANTÁ";7\r\n'
    ).encode("latin-1")

    colunas, por_uf = dividir_por_uf(io.BytesIO(corpo), "votacao_secao", tmp_path)

    assert sorted(por_uf) == ["AP", "RR"]
    rr = ler_csv_uf(por_uf["RR"], colunas)
    assert rr.height == 2
    assert rr["NM_MUNICIPIO"].to_list() == ["RORAINÓPOLIS", "CANTÁ"]
    assert rr["QT_VOTOS"].dtype.is_(rr["SG_UF"].dtype)  # tudo texto


def test_divide_por_uf_layout_legado_inclui_primeira_linha(tmp_path: Path) -> None:
    legado = TSE_COLUNAS_LEGADO["votacao_secao"]
    valores = ["x"] * len(legado)
    valores[legado.index("SIGLA_UF")] = "GO"
    linha = ";".join(f'"{v}"' for v in valores) + "\n"

    colunas, por_uf = dividir_por_uf(
        io.BytesIO((linha * 3).encode("latin-1")), "votacao_secao", tmp_path
    )

    assert ler_csv_uf(por_uf["GO"], colunas).height == 3

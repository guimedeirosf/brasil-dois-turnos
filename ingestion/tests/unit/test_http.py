from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest
import respx

from ingestion.http import ClienteHttp, ErroHttp

URL = "https://exemplo.test/arquivo.zip"


@respx.mock
def test_retry_em_503_depois_sucesso(http: ClienteHttp) -> None:
    rota = respx.get(URL).mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": True})]
    )
    assert http.get_json(URL) == {"ok": True}
    assert rota.call_count == 2


@respx.mock
def test_desiste_apos_tres_tentativas(http: ClienteHttp) -> None:
    rota = respx.get(URL).mock(return_value=httpx.Response(500))
    with pytest.raises(ErroHttp, match="3 tentativas"):
        http.get_json(URL)
    assert rota.call_count == 3


@respx.mock
def test_timeout_conta_como_falha_repetivel(http: ClienteHttp) -> None:
    respx.get(URL).mock(side_effect=[httpx.ReadTimeout("lento"), httpx.Response(200, text="ok")])
    assert http.get_texto(URL) == "ok"


@respx.mock
def test_erro_404_nao_repete(http: ClienteHttp) -> None:
    rota = respx.get(URL).mock(return_value=httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        http.get_json(URL)
    assert rota.call_count == 1


@respx.mock
def test_download_calcula_hash(http: ClienteHttp, tmp_path: Path) -> None:
    conteudo = b"x" * 3_000_000
    respx.get(URL).mock(return_value=httpx.Response(200, content=conteudo))

    download = http.baixar(URL, tmp_path / "a" / "arquivo.zip")

    assert download.tamanho == len(conteudo)
    assert download.sha256 == hashlib.sha256(conteudo).hexdigest()
    assert download.caminho.read_bytes() == conteudo


@respx.mock
def test_download_falho_nao_deixa_arquivo(http: ClienteHttp, tmp_path: Path) -> None:
    respx.get(URL).mock(return_value=httpx.Response(502))
    destino = tmp_path / "arquivo.zip"
    with pytest.raises(ErroHttp):
        http.baixar(URL, destino)
    assert not destino.exists()


@respx.mock
def test_cabecalho_gera_assinatura(http: ClienteHttp) -> None:
    respx.head(URL).mock(
        return_value=httpx.Response(
            200, headers={"content-length": "42", "etag": '"abc"', "last-modified": "ontem"}
        )
    )
    assert http.cabecalho(URL).assinatura() == '42|"abc"|ontem'

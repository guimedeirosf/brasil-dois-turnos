"""Cliente HTTP com retry exponencial, timeout e download em streaming."""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

STATUS_REPETIVEIS = {429, 500, 502, 503, 504}


class ErroHttp(RuntimeError):
    pass


@dataclass(frozen=True)
class Download:
    caminho: Path
    sha256: str
    tamanho: int


@dataclass(frozen=True)
class Cabecalho:
    tamanho: int | None
    etag: str | None
    modificado_em: str | None

    def assinatura(self) -> str:
        """Identifica a versao remota sem baixar o arquivo."""
        return f"{self.tamanho}|{self.etag}|{self.modificado_em}"


class ClienteHttp:
    def __init__(
        self,
        tentativas: int = 3,
        timeout_s: float = 120.0,
        espera_base_s: float = 2.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.tentativas = tentativas
        self.espera_base_s = espera_base_s
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout_s, connect=30.0),
            follow_redirects=True,
            headers={"User-Agent": "brasil-dois-turnos/0.1 (+github.com/brasil-dois-turnos)"},
        )

    def _com_retry(self, metodo: str, url: str, **kwargs: Any) -> httpx.Response:
        ultimo_erro: Exception | None = None
        for tentativa in range(1, self.tentativas + 1):
            try:
                resp = self._client.request(metodo, url, **kwargs)
                if resp.status_code in STATUS_REPETIVEIS:
                    raise ErroHttp(f"{resp.status_code} em {url}")
                resp.raise_for_status()
                return resp
            except (httpx.TransportError, ErroHttp) as erro:
                ultimo_erro = erro
                if tentativa < self.tentativas:
                    espera = self.espera_base_s * 2 ** (tentativa - 1)
                    log.warning("tentativa %d falhou (%s); nova em %.0fs", tentativa, erro, espera)
                    time.sleep(espera)
        raise ErroHttp(f"falhou apos {self.tentativas} tentativas: {url}") from ultimo_erro

    def get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        return self._com_retry("GET", url, params=params).json()

    def get_texto(self, url: str) -> str:
        return self._com_retry("GET", url).text

    def cabecalho(self, url: str) -> Cabecalho:
        resp = self._com_retry("HEAD", url)
        tamanho = resp.headers.get("content-length")
        return Cabecalho(
            tamanho=int(tamanho) if tamanho else None,
            etag=resp.headers.get("etag"),
            modificado_em=resp.headers.get("last-modified"),
        )

    def baixar(self, url: str, destino: Path) -> Download:
        """Baixa em streaming para disco, calculando o SHA-256 no caminho."""
        destino.parent.mkdir(parents=True, exist_ok=True)
        ultimo_erro: Exception | None = None
        for tentativa in range(1, self.tentativas + 1):
            sha = hashlib.sha256()
            tamanho = 0
            try:
                with self._client.stream("GET", url) as resp:
                    if resp.status_code in STATUS_REPETIVEIS:
                        raise ErroHttp(f"{resp.status_code} em {url}")
                    resp.raise_for_status()
                    with destino.open("wb") as arq:
                        for bloco in resp.iter_bytes(1 << 20):
                            arq.write(bloco)
                            sha.update(bloco)
                            tamanho += len(bloco)
                return Download(destino, sha.hexdigest(), tamanho)
            except (httpx.TransportError, ErroHttp) as erro:
                ultimo_erro = erro
                destino.unlink(missing_ok=True)
                if tentativa < self.tentativas:
                    time.sleep(self.espera_base_s * 2 ** (tentativa - 1))
        raise ErroHttp(f"download falhou apos {self.tentativas} tentativas: {url}") from ultimo_erro

    def close(self) -> None:
        self._client.close()

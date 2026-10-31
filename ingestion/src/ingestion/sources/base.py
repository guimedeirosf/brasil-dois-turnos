"""Contrato comum das fontes: discover -> pending -> fetch -> to_bronze."""

from __future__ import annotations

import logging
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from ingestion.config import Config
from ingestion.http import ClienteHttp, Download
from ingestion.manifest import Carga, Manifesto

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Particao:
    """Uma unidade de download. `rotulo` e a chave estavel no manifesto."""

    rotulo: str
    url: str
    params: dict[str, str] = field(default_factory=dict)


class Source(ABC):
    nome: str

    def __init__(self, cfg: Config, http: ClienteHttp, manifesto: Manifesto) -> None:
        self.cfg = cfg
        self.http = http
        self.manifesto = manifesto

    @abstractmethod
    def discover(self) -> list[Particao]:
        """Lista as particoes disponiveis na origem."""

    def assinatura(self, particao: Particao) -> str:
        """Versao remota (tamanho, ETag, data). Vazio = nao da para saber sem baixar."""
        return self.http.cabecalho(particao.url).assinatura()

    def pending(self, forcar: bool = False) -> list[tuple[Particao, str]]:
        """Particoes novas ou alteradas desde a ultima carga."""
        pendentes = []
        for particao in self.discover():
            assinatura = self.assinatura(particao)
            atual = assinatura and self.manifesto.esta_atual(self.nome, particao.rotulo, assinatura)
            if forcar or not atual:
                pendentes.append((particao, assinatura))
            else:
                log.info("%s %s sem mudancas", self.nome, particao.rotulo)
        return pendentes

    def fetch(self, particao: Particao, pasta: Path) -> Download:
        nome = particao.url.rsplit("/", 1)[-1].split("?", 1)[0] or "download"
        return self.http.baixar(particao.url, pasta / nome)

    @abstractmethod
    def to_bronze(self, particao: Particao, download: Download) -> int:
        """Converte o arquivo baixado em Parquet na Bronze. Devolve o total de linhas."""

    def run(self, forcar: bool = False) -> list[Carga]:
        cargas = []
        for particao, assinatura in self.pending(forcar):
            # O diretorio temporario some ao fim de cada particao: o zip e descartado
            with tempfile.TemporaryDirectory(prefix=f"{self.nome}-") as tmp:
                download = self.fetch(particao, Path(tmp))
                anterior = self.manifesto.ultima(self.nome, particao.rotulo)
                if not forcar and anterior and anterior.sha256 == download.sha256:
                    log.info("%s %s: conteudo identico, nada a gravar", self.nome, particao.rotulo)
                    continue
                linhas = self.to_bronze(particao, download)
            carga = self.manifesto.registrar(
                fonte=self.nome,
                particao=particao.rotulo,
                url=particao.url,
                sha256=download.sha256,
                linhas=linhas,
                assinatura_remota=assinatura,
            )
            log.info("%s %s: %d linhas", self.nome, particao.rotulo, linhas)
            cargas.append(carga)
        return cargas

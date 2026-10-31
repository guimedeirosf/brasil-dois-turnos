"""Controle de cargas: uma entrada por (fonte, particao), gravada em JSON versionado.

O arquivo e ordenado e com indentacao fixa para gerar diffs pequenos no commit mensal.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ingestion import __version__


@dataclass(frozen=True)
class Carga:
    fonte: str
    particao: str
    url: str
    sha256: str
    linhas: int
    assinatura_remota: str
    carregado_em: str
    versao_codigo: str


class Manifesto:
    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        self._cargas: dict[str, Carga] = {}
        if caminho.exists():
            for item in json.loads(caminho.read_text(encoding="utf-8")):
                carga = Carga(**item)
                self._cargas[self._chave(carga.fonte, carga.particao)] = carga

    @staticmethod
    def _chave(fonte: str, particao: str) -> str:
        return f"{fonte}::{particao}"

    def ultima(self, fonte: str, particao: str) -> Carga | None:
        return self._cargas.get(self._chave(fonte, particao))

    def esta_atual(self, fonte: str, particao: str, assinatura_remota: str) -> bool:
        carga = self.ultima(fonte, particao)
        return carga is not None and carga.assinatura_remota == assinatura_remota

    def registrar(
        self,
        fonte: str,
        particao: str,
        url: str,
        sha256: str,
        linhas: int,
        assinatura_remota: str,
    ) -> Carga:
        carga = Carga(
            fonte=fonte,
            particao=particao,
            url=url,
            sha256=sha256,
            linhas=linhas,
            assinatura_remota=assinatura_remota,
            carregado_em=datetime.now(UTC).isoformat(timespec="seconds"),
            versao_codigo=__version__,
        )
        self._cargas[self._chave(fonte, particao)] = carga
        self.salvar()
        return carga

    def cargas(self) -> list[Carga]:
        return [self._cargas[k] for k in sorted(self._cargas)]

    def salvar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        conteudo = json.dumps([asdict(c) for c in self.cargas()], ensure_ascii=False, indent=2)
        self.caminho.write_text(conteudo + "\n", encoding="utf-8")

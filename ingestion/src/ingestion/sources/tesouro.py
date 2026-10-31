"""Tesouro Nacional (divida publica federal, Brasil/mes).

Fase 4 do roteiro. Antes de implementar, confirme URL e layout atuais
(API/CSV do Tesouro Transparente)
e registre-os em config.py.
"""

from __future__ import annotations

from ingestion.http import Download
from ingestion.sources.base import Particao, Source


class TesouroSource(Source):
    nome = "tesouro"

    def discover(self) -> list[Particao]:
        raise NotImplementedError("fonte prevista para a fase 4")

    def to_bronze(self, particao: Particao, download: Download) -> int:
        raise NotImplementedError("fonte prevista para a fase 4")

"""Receita Federal, CNPJ (empresas e MEI ativos por municipio).

Fase 4 do roteiro. Antes de implementar, confirme URL e layout atuais
(dump mensal de Dados Abertos CNPJ)
e registre-os em config.py.
"""

from __future__ import annotations

from ingestion.http import Download
from ingestion.sources.base import Particao, Source


class CnpjSource(Source):
    nome = "cnpj"

    def discover(self) -> list[Particao]:
        raise NotImplementedError("fonte prevista para a fase 4")

    def to_bronze(self, particao: Particao, download: Download) -> int:
        raise NotImplementedError("fonte prevista para a fase 4")

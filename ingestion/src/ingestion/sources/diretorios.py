"""Diretorio de municipios do IBGE e de-para de codigos TSE <-> IBGE.

Usa downloads diretos (API de localidades do IBGE e CSV publico do de-para) em vez do BigQuery
da Base dos Dados, para nao depender de conta Google.
"""

from __future__ import annotations

import json

import polars as pl

from ingestion.config import IBGE_MUNICIPIOS_URL, TSE_IBGE_DEPARA_URL
from ingestion.http import Download
from ingestion.sources.base import Particao, Source
from ingestion.storage import gravar_bronze


class DiretoriosSource(Source):
    nome = "diretorios"

    def discover(self) -> list[Particao]:
        return [
            Particao("municipios_ibge", IBGE_MUNICIPIOS_URL, {"formato": "json"}),
            Particao("municipios_tse", TSE_IBGE_DEPARA_URL, {"formato": "csv"}),
        ]

    def assinatura(self, particao: Particao) -> str:
        return ""  # sempre baixa; o hash do conteudo evita regravar o que nao mudou

    def to_bronze(self, particao: Particao, download: Download) -> int:
        if particao.params["formato"] == "json":
            dados = json.loads(download.caminho.read_text(encoding="utf-8"))
            df = pl.json_normalize(dados, separator="__", infer_schema_length=None)
        else:
            df = pl.read_csv(download.caminho, infer_schema=False, encoding="utf8")
        gravar_bronze(df, self.cfg.bronze_dir, f"diretorios/{particao.rotulo}", {}, download.sha256)
        return df.height

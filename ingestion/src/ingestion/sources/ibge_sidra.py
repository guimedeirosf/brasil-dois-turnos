"""IBGE SIDRA: uma requisicao por tabela e periodo."""

from __future__ import annotations

import json

import polars as pl

from ingestion.config import SIDRA_PERIODOS_URL, SIDRA_TABELAS, SIDRA_URL, Config
from ingestion.http import ClienteHttp, Download
from ingestion.manifest import Manifesto
from ingestion.sources.base import Particao, Source
from ingestion.storage import gravar_bronze


class SidraSource(Source):
    nome = "ibge_sidra"

    def __init__(self, cfg: Config, http: ClienteHttp, manifesto: Manifesto, tabela: str) -> None:
        super().__init__(cfg, http, manifesto)
        if tabela not in SIDRA_TABELAS:
            raise ValueError(f"tabela {tabela!r} fora de SIDRA_TABELAS")
        self.tabela = tabela
        self.spec = SIDRA_TABELAS[tabela]

    def discover(self) -> list[Particao]:
        periodos = self.http.get_json(SIDRA_PERIODOS_URL.format(tabela=self.spec.tabela))
        return [
            Particao(
                rotulo=f"{self.tabela}/periodo={p['id']}",
                url=SIDRA_URL + self.spec.consulta.format(periodo=p["id"]),
                params={"periodo": str(p["id"])},
            )
            for p in periodos
        ]

    def assinatura(self, particao: Particao) -> str:
        # Periodos fechados nao mudam; revisoes do IBGE entram com --forcar
        return "periodo-publicado"

    def to_bronze(self, particao: Particao, download: Download) -> int:
        dados = json.loads(download.caminho.read_text(encoding="utf-8"))
        # A primeira linha da resposta e o dicionario de colunas; os nomes originais ficam
        df = pl.DataFrame(dados[1:], schema=dict.fromkeys(dados[0], pl.Utf8))
        gravar_bronze(
            df,
            self.cfg.bronze_dir,
            f"ibge_sidra/{self.tabela}",
            {"periodo": particao.params["periodo"]},
            download.sha256,
        )
        return df.height

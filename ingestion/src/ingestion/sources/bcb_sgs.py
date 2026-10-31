"""Banco Central, Sistema Gerenciador de Series (SGS)."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl

from ingestion.config import BCB_SERIES, BCB_SGS_URL, Config
from ingestion.http import ClienteHttp, Download
from ingestion.manifest import Manifesto
from ingestion.sources.base import Particao, Source
from ingestion.storage import gravar_bronze

# A API recusa janelas maiores que 10 anos
ANOS_POR_JANELA = 10


def janelas(desde: date, ate: date) -> list[tuple[date, date]]:
    resultado = []
    inicio = desde
    while inicio <= ate:
        fim = min(date(inicio.year + ANOS_POR_JANELA - 1, 12, 31), ate)
        resultado.append((inicio, fim))
        inicio = fim + timedelta(days=1)
    return resultado


class BcbSource(Source):
    nome = "bcb_sgs"

    def __init__(
        self,
        cfg: Config,
        http: ClienteHttp,
        manifesto: Manifesto,
        desde: date,
        ate: date | None = None,
        series: dict[str, int] | None = None,
    ) -> None:
        super().__init__(cfg, http, manifesto)
        self.desde = desde
        self.ate = ate or date.today()
        self.series = series or BCB_SERIES

    def discover(self) -> list[Particao]:
        return [
            Particao(
                rotulo=f"serie={nome}",
                url=BCB_SGS_URL.format(codigo=codigo),
                params={"serie": nome, "codigo": str(codigo)},
            )
            for nome, codigo in sorted(self.series.items())
        ]

    def assinatura(self, particao: Particao) -> str:
        return ""

    def fetch(self, particao: Particao, pasta: Path) -> Download:
        registros: list[dict[str, str]] = []
        for inicio, fim in janelas(self.desde, self.ate):
            registros.extend(
                self.http.get_json(
                    particao.url,
                    params={
                        "formato": "json",
                        "dataInicial": inicio.strftime("%d/%m/%Y"),
                        "dataFinal": fim.strftime("%d/%m/%Y"),
                    },
                )
            )
        conteudo = json.dumps(registros, ensure_ascii=False).encode()
        destino = pasta / f"{particao.params['serie']}.json"
        destino.write_bytes(conteudo)
        return Download(destino, hashlib.sha256(conteudo).hexdigest(), len(conteudo))

    def to_bronze(self, particao: Particao, download: Download) -> int:
        dados = json.loads(download.caminho.read_text(encoding="utf-8"))
        df = pl.DataFrame(dados, schema={"data": pl.Utf8, "valor": pl.Utf8}).with_columns(
            pl.lit(particao.params["codigo"]).alias("codigo_sgs")
        )
        gravar_bronze(
            df,
            self.cfg.bronze_dir,
            "bcb_sgs",
            {"serie": particao.params["serie"]},
            download.sha256,
        )
        return df.height

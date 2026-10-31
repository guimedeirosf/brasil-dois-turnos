from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import httpx
import polars as pl
import respx

from ingestion.config import Config
from ingestion.http import ClienteHttp, Download
from ingestion.manifest import Manifesto
from ingestion.sources.base import Particao, Source
from ingestion.sources.bcb_sgs import BcbSource, janelas
from ingestion.sources.ibge_sidra import SidraSource
from ingestion.storage import caminho_bronze, gravar_bronze


class FonteFalsa(Source):
    nome = "falsa"

    def __init__(self, *args: object, assinatura: str = "v1") -> None:
        super().__init__(*args)  # type: ignore[arg-type]
        self._assinatura = assinatura
        self.convertidas: list[str] = []

    def discover(self) -> list[Particao]:
        return [Particao("p1", "https://exemplo.test/p1.csv")]

    def assinatura(self, particao: Particao) -> str:
        return self._assinatura

    def to_bronze(self, particao: Particao, download: Download) -> int:
        self.convertidas.append(particao.rotulo)
        return 1


@respx.mock
def test_run_pula_o_que_ja_foi_carregado(
    cfg: Config, http: ClienteHttp, manifesto: Manifesto
) -> None:
    respx.get("https://exemplo.test/p1.csv").mock(return_value=httpx.Response(200, text="a"))
    fonte = FonteFalsa(cfg, http, manifesto)

    assert len(fonte.run()) == 1
    assert fonte.run() == []  # mesma assinatura remota: nada pendente
    assert fonte.convertidas == ["p1"]


@respx.mock
def test_run_nao_regrava_conteudo_identico(
    cfg: Config, http: ClienteHttp, manifesto: Manifesto
) -> None:
    respx.get("https://exemplo.test/p1.csv").mock(return_value=httpx.Response(200, text="a"))
    FonteFalsa(cfg, http, manifesto, assinatura="").run()

    fonte = FonteFalsa(cfg, http, manifesto, assinatura="")
    assert fonte.run() == []
    assert fonte.convertidas == []


def test_gravar_bronze_texto_auditoria_idempotente(cfg: Config) -> None:
    df = pl.DataFrame({"QT_VOTOS": [1, 2], "NM": ["a", "b"]})
    for _ in range(2):
        destino = gravar_bronze(df, cfg.bronze_dir, "tse/x", {"ano": "2026"}, "hash")

    assert destino == caminho_bronze(cfg.bronze_dir, "tse/x", {"ano": "2026"})
    lido = pl.read_parquet(destino)
    assert lido.height == 2
    assert lido.schema["QT_VOTOS"] == pl.Utf8
    assert lido["_particao"].unique().to_list() == ["ano=2026"]
    assert {"_fonte", "_carregado_em", "_hash_arquivo"} <= set(lido.columns)
    assert len(list(destino.parent.iterdir())) == 1


def test_janelas_bcb_de_dez_anos() -> None:
    resultado = janelas(date(1989, 1, 1), date(2026, 10, 30))
    assert resultado[0] == (date(1989, 1, 1), date(1998, 12, 31))
    assert resultado[-1] == (date(2019, 1, 1), date(2026, 10, 30))
    assert len(resultado) == 4


@respx.mock
def test_bcb_junta_janelas_e_grava(cfg: Config, http: ClienteHttp, manifesto: Manifesto) -> None:
    rota = respx.get(url__startswith="https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/").mock(
        side_effect=[
            httpx.Response(200, json=[{"data": "01/01/2010", "valor": "0.5"}]),
            httpx.Response(200, json=[{"data": "01/01/2020", "valor": "0.2"}]),
        ]
    )
    fonte = BcbSource(cfg, http, manifesto, date(2010, 1, 1), date(2020, 12, 31), {"ipca": 433})

    cargas = fonte.run()

    assert rota.call_count == 2
    assert cargas[0].linhas == 2
    lido = pl.read_parquet(caminho_bronze(cfg.bronze_dir, "bcb_sgs", {"serie": "ipca"}))
    assert lido["codigo_sgs"].unique().to_list() == ["433"]


@respx.mock
def test_sidra_uma_particao_por_periodo(
    cfg: Config, http: ClienteHttp, manifesto: Manifesto
) -> None:
    respx.get("https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos").mock(
        return_value=httpx.Response(200, json=[{"id": "2024"}, {"id": "2025"}])
    )
    resposta = [{"V": "Valor", "D1C": "Municipio"}, {"V": "500", "D1C": "1400100"}]
    respx.get(url__startswith="https://apisidra.ibge.gov.br/values/t/6579").mock(
        return_value=httpx.Response(200, content=json.dumps(resposta).encode())
    )
    fonte = SidraSource(cfg, http, manifesto, "populacao_estimada")

    assert [p.rotulo for p in fonte.discover()] == [
        "populacao_estimada/periodo=2024",
        "populacao_estimada/periodo=2025",
    ]
    fonte.run()
    assert fonte.run() == []  # periodos publicados nao sao baixados de novo
    lido = pl.read_parquet(
        caminho_bronze(cfg.bronze_dir, "ibge_sidra/populacao_estimada", {"periodo": "2025"})
    )
    assert lido.select("V", "D1C").row(0) == ("500", "1400100")


def test_caminho_bronze_hive(tmp_path: Path) -> None:
    caminho = caminho_bronze(tmp_path, "tse/votacao", {"ano": "2026", "uf": "RR"})
    assert caminho.relative_to(tmp_path).as_posix() == "tse/votacao/ano=2026/uf=RR/part-0.parquet"

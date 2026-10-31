"""Monta uma Bronze a partir das fixtures versionadas (ambiente `ci` e testes).

Passa pelos mesmos `to_bronze` das fontes reais, so trocando o download pelo arquivo local.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from ingestion.config import BCB_SERIES, RAIZ_REPO, Config
from ingestion.http import ClienteHttp, Download
from ingestion.manifest import Manifesto
from ingestion.sources.base import Particao
from ingestion.sources.bcb_sgs import BcbSource
from ingestion.sources.diretorios import DiretoriosSource
from ingestion.sources.ibge_sidra import SidraSource
from ingestion.sources.tse import TseSource

PASTA_FIXTURES = RAIZ_REPO / "ingestion" / "tests" / "fixtures"
ANO_FIXTURE = 2026


def _download(caminho: Path) -> Download:
    conteudo = caminho.read_bytes()
    return Download(caminho, hashlib.sha256(conteudo).hexdigest(), len(conteudo))


def _zipar(csv: Path, destino: Path) -> Download:
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv, csv.name)
    return _download(destino)


def carregar_fixtures(cfg: Config, pasta: Path = PASTA_FIXTURES) -> dict[str, int]:
    http = ClienteHttp()
    with tempfile.TemporaryDirectory() as tmp:
        manifesto = Manifesto(Path(tmp) / "manifesto.json")
        linhas: dict[str, int] = {}

        tse = TseSource(cfg, http, manifesto, ANO_FIXTURE, "presidente")
        for particao in tse.discover():
            tabela = particao.params["tabela"]
            csv = pasta / "tse" / f"{tabela}_{ANO_FIXTURE}_BR.csv"
            linhas[tabela] = tse.to_bronze(particao, _zipar(csv, Path(tmp) / f"{tabela}.zip"))

        diretorios = DiretoriosSource(cfg, http, manifesto)
        for particao in diretorios.discover():
            extensao = particao.params["formato"]
            arquivo = pasta / "diretorios" / f"{particao.rotulo}.{extensao}"
            linhas[particao.rotulo] = diretorios.to_bronze(particao, _download(arquivo))

        bcb = BcbSource(cfg, http, manifesto, desde=date(2025, 1, 1))
        for arquivo in sorted((pasta / "bcb_sgs").glob("*.json")):
            serie = arquivo.stem
            particao = Particao(
                f"serie={serie}", "", {"serie": serie, "codigo": str(BCB_SERIES[serie])}
            )
            linhas[f"bcb:{serie}"] = bcb.to_bronze(particao, _download(arquivo))

        for arquivo in sorted((pasta / "ibge_sidra").glob("*.json")):
            tabela, periodo = arquivo.stem.rsplit("_", 1)
            sidra = SidraSource(cfg, http, manifesto, tabela)
            particao = Particao(f"{tabela}/periodo={periodo}", "", {"periodo": periodo})
            linhas[f"sidra:{tabela}"] = sidra.to_bronze(particao, _download(arquivo))
    http.close()
    return linhas


if __name__ == "__main__":
    print(json.dumps(carregar_fixtures(Config.from_env()), indent=2))

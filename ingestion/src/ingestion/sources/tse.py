"""TSE Dados Abertos: votacao por secao, detalhe da apuracao e candidatos.

Os CSVs do TSE sao latin-1 com separador ';'. O arquivo de presidente ("_BR") traz todas as UFs
num CSV so (1,5 GB em 2026); por isso o CSV e lido em streaming e dividido por UF em arquivos
temporarios UTF-8, e cada UF vira um Parquet de cada vez.
"""

from __future__ import annotations

import io
import re
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import IO

import polars as pl

from ingestion.config import TSE_COLUNAS_LEGADO, Config, arquivos_tse
from ingestion.http import ClienteHttp, Download
from ingestion.manifest import Manifesto
from ingestion.sources.base import Particao, Source
from ingestion.storage import gravar_bronze

COLUNAS_UF = ("SG_UF", "SIGLA_UF")
COLUNAS_CABECALHO = ("ANO_ELEICAO", "DT_GERACAO")


def _campos(linha: str) -> list[str]:
    return [c.strip().strip('"') for c in linha.rstrip("\r\n").split(";")]


def detectar_layout(primeira_linha: str, tabela: str) -> tuple[list[str], bool]:
    """Devolve (colunas, tem_cabecalho). Arquivos antigos do TSE nao tem cabecalho."""
    campos = _campos(primeira_linha)
    if any(c in campos for c in COLUNAS_CABECALHO):
        return campos, True
    legado = TSE_COLUNAS_LEGADO.get(tabela)
    if legado is None or len(legado) != len(campos):
        raise ValueError(f"layout desconhecido para {tabela}: {len(campos)} colunas sem cabecalho")
    return list(legado), False


def _linhas_latin1(arquivo: IO[bytes]) -> Iterator[str]:
    yield from io.TextIOWrapper(arquivo, encoding="latin-1", newline="")


def dividir_por_uf(
    arquivo: IO[bytes], tabela: str, pasta: Path
) -> tuple[list[str], dict[str, Path]]:
    """Le o CSV em streaming e grava um CSV UTF-8 por UF (sem cabecalho)."""
    linhas = _linhas_latin1(arquivo)
    primeira = next(linhas)
    colunas, tem_cabecalho = detectar_layout(primeira, tabela)
    indice_uf = next(i for i, c in enumerate(colunas) if c in COLUNAS_UF)
    caminhos: dict[str, Path] = {}
    with ExitStack() as pilha:
        saidas: dict[str, IO[str]] = {}

        def escrever(linha: str) -> None:
            if not linha.strip():
                return
            uf = linha.split(";", indice_uf + 1)[indice_uf].strip().strip('"')
            if uf not in saidas:
                caminhos[uf] = pasta / f"{tabela}_{uf}.csv"
                saidas[uf] = pilha.enter_context(
                    caminhos[uf].open("w", encoding="utf-8", newline="")
                )
            saidas[uf].write(linha)

        if not tem_cabecalho:
            escrever(primeira)
        for linha in linhas:
            escrever(linha)
    return colunas, caminhos


def ler_csv_uf(caminho: Path, colunas: list[str]) -> pl.DataFrame:
    return pl.read_csv(
        caminho,
        separator=";",
        has_header=False,
        new_columns=colunas,
        infer_schema=False,
        quote_char='"',
        encoding="utf8",
    )


class TseSource(Source):
    nome = "tse"

    def __init__(
        self,
        cfg: Config,
        http: ClienteHttp,
        manifesto: Manifesto,
        ano: int,
        cargo: str,
        ufs: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(cfg, http, manifesto)
        self.ano = ano
        self.cargo = cargo
        self.ufs = ufs
        self._membros = {a.tabela: a.membro for a in arquivos_tse(ano, cargo)}

    def discover(self) -> list[Particao]:
        # Carga parcial (amostra de UFs no dev) fica registrada separada da carga completa
        sufixo = f"/ufs={','.join(sorted(self.ufs))}" if self.ufs else ""
        return [
            Particao(
                rotulo=f"{a.tabela}/ano={self.ano}/cargo={self.cargo}{sufixo}",
                url=a.url,
                params={"tabela": a.tabela},
            )
            for a in arquivos_tse(self.ano, self.cargo)
        ]

    def to_bronze(self, particao: Particao, download: Download) -> int:
        tabela = particao.params["tabela"]
        padrao = re.compile(self._membros[tabela], re.IGNORECASE)
        total = 0
        with zipfile.ZipFile(download.caminho) as zf:
            membros = [n for n in zf.namelist() if padrao.fullmatch(Path(n).name)]
            if not membros:
                raise FileNotFoundError(f"nenhum CSV {padrao.pattern} em {particao.url}")
            for membro in membros:
                with tempfile.TemporaryDirectory(prefix="tse-uf-") as tmp, zf.open(membro) as arq:
                    colunas, por_uf = dividir_por_uf(arq, tabela, Path(tmp))
                    for uf in sorted(por_uf):
                        if self.ufs and uf not in self.ufs:
                            continue
                        df = ler_csv_uf(por_uf[uf], colunas)
                        gravar_bronze(
                            df,
                            self.cfg.bronze_dir,
                            f"tse/{tabela}",
                            {"ano": str(self.ano), "cargo": self.cargo, "uf": uf},
                            download.sha256,
                        )
                        total += df.height
                        por_uf[uf].unlink()
        return total

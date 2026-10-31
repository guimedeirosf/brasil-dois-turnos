"""Caminhos, URLs e variaveis de ambiente.

URLs, codigos de series e layouts conferidos nos portais oficiais em 2026-10-30.
Ao incluir uma fonte ou eleicao nova, confira de novo antes de rodar a carga.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[3]

UFS = (
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
)  # fmt: skip
UF_EXTERIOR = "ZZ"

# --- TSE -----------------------------------------------------------------------------

TSE_CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"

# Codigo CD_CARGO do TSE por cargo
TSE_CARGOS = {"presidente": 1, "governador": 3, "prefeito": 11}


@dataclass(frozen=True)
class ArquivoTse:
    """Um zip do TSE e o padrao dos CSVs que interessam dentro dele."""

    tabela: str
    url: str
    membro: str  # regex aplicada ao nome do arquivo dentro do zip


def arquivos_tse(ano: int, cargo: str) -> list[ArquivoTse]:
    """Arquivos do TSE necessarios para uma eleicao.

    Presidente (eleicoes federais): votacao e detalhe vem num CSV unico "_BR" com todas as UFs
    e o exterior (ZZ); candidatos vem em consulta_cand_<ano>_BR.csv.
    Governador e prefeito: um CSV por UF.
    """
    if cargo == "presidente":
        return [
            ArquivoTse(
                "votacao_secao",
                f"{TSE_CDN}/votacao_secao/votacao_secao_{ano}_BR.zip",
                rf"votacao_secao_{ano}_BR\.csv",
            ),
            ArquivoTse(
                "detalhe_votacao_secao",
                f"{TSE_CDN}/detalhe_votacao_secao/detalhe_votacao_secao_{ano}.zip",
                rf"detalhe_votacao_secao_{ano}_BR\.csv",
            ),
            ArquivoTse(
                "consulta_cand",
                f"{TSE_CDN}/consulta_cand/consulta_cand_{ano}.zip",
                rf"consulta_cand_{ano}_BR\.csv",
            ),
        ]
    raise NotImplementedError(f"cargo {cargo!r} entra na fase 6")


# Layouts antigos (sem cabecalho). Conferir contra o leiame.pdf de cada ano antes da carga.
TSE_COLUNAS_LEGADO: dict[str, tuple[str, ...]] = {
    "votacao_secao": (
        "DATA_GERACAO", "HORA_GERACAO", "ANO_ELEICAO", "NUM_TURNO", "DESCRICAO_ELEICAO",
        "SIGLA_UF", "SIGLA_UE", "CODIGO_MUNICIPIO", "NOME_MUNICIPIO", "NUM_ZONA", "NUM_SECAO",
        "CODIGO_CARGO", "DESCRICAO_CARGO", "NUM_VOTAVEL", "QTDE_VOTOS",
    ),
}  # fmt: skip

# --- Diretorios (de-para TSE <-> IBGE) ------------------------------------------------

IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
TSE_IBGE_DEPARA_URL = (
    "https://raw.githubusercontent.com/betafcc/Municipios-Brasileiros-TSE/"
    "master/municipios_brasileiros_tse.csv"
)

# --- BCB SGS -------------------------------------------------------------------------

BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

# nome -> codigo SGS. Todas mensais.
BCB_SERIES: dict[str, int] = {
    "selic_mes_anualizada": 4189,
    "ipca_var_mensal": 433,
    "cambio_venda_media_mes": 3698,
    "dlsp_pct_pib": 4513,
    "dbgg_pct_pib": 13762,
    "desocupacao_pnad": 24369,
    "pib_mensal_corrente": 4380,
}
# Divida externa: o codigo 3546 devolve valor compativel com reservas internacionais.
# Confirmar a serie correta no SGS antes de incluir aqui.

# --- IBGE SIDRA ----------------------------------------------------------------------

SIDRA_URL = "https://apisidra.ibge.gov.br/values"
SIDRA_PERIODOS_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/periodos"


@dataclass(frozen=True)
class TabelaSidra:
    tabela: int
    consulta: str  # caminho com {periodo}; uma requisicao por periodo (limite de 100 mil valores)


SIDRA_TABELAS: dict[str, TabelaSidra] = {
    "populacao_estimada": TabelaSidra(6579, "/t/6579/n6/all/v/9324/p/{periodo}"),
    "pib_municipal": TabelaSidra(5938, "/t/5938/n6/all/v/37/p/{periodo}"),
}


# --- Ambiente ------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    data_dir: Path
    bronze_dir: Path
    gold_dir: Path
    warehouse: Path
    manifesto: Path
    ambiente: str = "dev"
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    timeout_s: float = 120.0
    tentativas: int = 3
    extras: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> Config:
        data_dir = Path(os.environ.get("DATA_DIR", RAIZ_REPO / "data"))
        return cls(
            data_dir=data_dir,
            bronze_dir=Path(os.environ.get("BRONZE_DIR", data_dir / "bronze")),
            gold_dir=Path(os.environ.get("GOLD_DIR", data_dir / "gold")),
            warehouse=Path(os.environ.get("WAREHOUSE_PATH", data_dir / "warehouse.duckdb")),
            manifesto=Path(os.environ.get("MANIFEST_PATH", RAIZ_REPO / "manifest" / "bronze.json")),
            ambiente=os.environ.get("AMBIENTE", "dev"),
            r2_account_id=os.environ.get("R2_ACCOUNT_ID"),
            r2_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
            r2_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
            r2_bucket=os.environ.get("R2_BUCKET"),
        )

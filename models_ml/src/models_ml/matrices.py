"""Monta X (origem no 1o turno), T (destino no 2o) e N (aptos) por secao.

Regras de pareamento entre turnos:
- junta por (uf, cod_municipio_tse, zona, secao);
- descarta secoes sem par, com variacao de aptos acima de 2% ou com menos de 50 aptos;
- se o descarte passar de 5% dos aptos, a execucao falha.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import numpy.typing as npt
import polars as pl

ORIGENS = ("CAND_A", "CAND_B", "ESQ", "CENTRO", "DIR", "BRANCO", "NULO", "ABST")
DESTINOS = ("CAND_A", "CAND_B", "BRANCO", "NULO", "ABST")

COLUNA_POR_CATEGORIA = {
    "CAND_A": "votos_cand_a",
    "CAND_B": "votos_cand_b",
    "ESQ": "votos_esq",
    "CENTRO": "votos_centro",
    "DIR": "votos_dir",
    "BRANCO": "brancos",
    "NULO": "nulos",
    "ABST": "abstencao",
}
CHAVE_SECAO = ("uf", "cod_municipio_tse", "zona", "secao")

VARIACAO_MAX_APTOS = 0.02
APTOS_MIN = 50
DESCARTE_MAX = 0.05


class DescarteExcessivo(RuntimeError):
    pass


@dataclass(frozen=True)
class Auditoria:
    abrangencia: str
    secoes_1t: int
    secoes_pareadas: int
    secoes_sem_par: int
    secoes_variacao_aptos: int
    secoes_poucos_aptos: int
    aptos_1t: int
    aptos_descartados: int

    @property
    def pct_aptos_descartados(self) -> float:
        return self.aptos_descartados / self.aptos_1t if self.aptos_1t else 0.0

    def como_dict(self) -> dict[str, object]:
        return {**asdict(self), "pct_aptos_descartados": self.pct_aptos_descartados}


@dataclass(frozen=True)
class Matrizes:
    x: npt.NDArray[np.float64]  # secoes x 8, proporcoes sobre os aptos do 1o turno
    t: npt.NDArray[np.float64]  # secoes x 5, proporcoes sobre os aptos do 2o turno
    n: npt.NDArray[np.int64]  # aptos no 1o turno
    contagens_origem: npt.NDArray[np.float64]  # secoes x 8, em eleitores
    contagens_destino: npt.NDArray[np.float64]  # secoes x 5, em eleitores
    municipios: npt.NDArray[np.int64]
    zonas: npt.NDArray[np.int64]


def ler_secoes(entrada: str, ano: int, cargo: str, uf: str | None = None) -> pl.DataFrame:
    """Le fct_secao_resumo da Gold (pasta local ou URL do R2)."""
    caminho = f"{entrada.rstrip('/')}/fct_secao_resumo/ano={ano}/cargo={cargo}/part-0.parquet"
    tabela = pl.scan_parquet(caminho)
    if uf:
        tabela = tabela.filter(pl.col("uf") == uf)
    return tabela.collect()


def parear_secoes(secoes: pl.DataFrame, abrangencia: str) -> tuple[pl.DataFrame, Auditoria]:
    colunas = [*CHAVE_SECAO, "aptos", *COLUNA_POR_CATEGORIA.values()]
    t1 = secoes.filter(pl.col("turno") == 1).select(colunas)
    t2 = secoes.filter(pl.col("turno") == 2).select(colunas)
    juntas = t1.join(t2, on=list(CHAVE_SECAO), how="left", suffix="_2t")

    sem_par = pl.col("aptos_2t").is_null()
    variacao = (pl.col("aptos_2t") - pl.col("aptos")).abs() / pl.col("aptos") > VARIACAO_MAX_APTOS
    poucos = pl.col("aptos") < APTOS_MIN
    juntas = juntas.with_columns(
        motivo=pl.when(sem_par)
        .then(pl.lit("sem_par"))
        .when(poucos)
        .then(pl.lit("poucos_aptos"))
        .when(variacao)
        .then(pl.lit("variacao_aptos"))
        .otherwise(pl.lit(None))
    )
    descartes = juntas.filter(pl.col("motivo").is_not_null())
    contagem = dict(descartes.group_by("motivo").len().iter_rows())
    auditoria = Auditoria(
        abrangencia=abrangencia,
        secoes_1t=t1.height,
        secoes_pareadas=juntas.height - descartes.height,
        secoes_sem_par=int(contagem.get("sem_par", 0)),
        secoes_variacao_aptos=int(contagem.get("variacao_aptos", 0)),
        secoes_poucos_aptos=int(contagem.get("poucos_aptos", 0)),
        aptos_1t=int(t1["aptos"].sum()),
        aptos_descartados=int(descartes["aptos"].sum()),
    )
    return juntas.filter(pl.col("motivo").is_null()).drop("motivo"), auditoria


def verificar_descarte(auditoria: Auditoria, limite: float = DESCARTE_MAX) -> None:
    if auditoria.pct_aptos_descartados > limite:
        raise DescarteExcessivo(
            f"{auditoria.abrangencia}: {auditoria.pct_aptos_descartados:.1%} dos aptos descartados"
            f" (limite {limite:.0%})"
        )


def montar_matrizes(pareadas: pl.DataFrame) -> Matrizes:
    origem = pareadas.select([COLUNA_POR_CATEGORIA[c] for c in ORIGENS]).to_numpy().astype(float)
    destino = (
        pareadas.select([f"{COLUNA_POR_CATEGORIA[c]}_2t" for c in DESTINOS])
        .to_numpy()
        .astype(float)
    )
    aptos_1t = pareadas["aptos"].to_numpy().astype(np.int64)
    aptos_2t = pareadas["aptos_2t"].to_numpy().astype(float)
    return Matrizes(
        x=origem / origem.sum(axis=1, keepdims=True),
        t=destino / aptos_2t[:, None],
        n=aptos_1t,
        contagens_origem=origem,
        contagens_destino=destino,
        municipios=pareadas["cod_municipio_tse"].to_numpy().astype(np.int64),
        zonas=pareadas["zona"].to_numpy().astype(np.int64),
    )


def subconjunto(m: Matrizes, mascara: npt.NDArray[np.bool_]) -> Matrizes:
    return Matrizes(
        x=m.x[mascara],
        t=m.t[mascara],
        n=m.n[mascara],
        contagens_origem=m.contagens_origem[mascara],
        contagens_destino=m.contagens_destino[mascara],
        municipios=m.municipios[mascara],
        zonas=m.zonas[mascara],
    )

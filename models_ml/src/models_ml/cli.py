"""python -m models_ml <comando>

    inferir  --ano 2026 --cargo presidente --uf GO --entrada data/gold --saida data/inferencia
    agregar  --ano 2026 --cargo presidente --parciais data/inferencia --gold data/gold

`inferir` roda uma UF (um job da matriz do Actions) e grava as amostras posteriores.
`agregar` valida cada UF, agrega o Brasil e grava fct_transicao_estimada e a auditoria.
Codigos de saida do `agregar`: 0 aprovado, 2 reprovado (bloqueia), 3 revisao manual.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import polars as pl

from models_ml.clustering import SECOES_POR_GRUPO, agrupar
from models_ml.ecological import (
    ConfigAmostragem,
    ResultadoEI,
    ajustar,
    amostras_para_tabela,
    combinar,
    resumir,
    tabela_para_amostras,
)
from models_ml.matrices import (
    ler_secoes,
    montar_matrizes,
    parear_secoes,
    subconjunto,
    verificar_descarte,
)
from models_ml.validate import APROVADO, REPROVADO, REVISAO, Relatorio, validar

log = logging.getLogger("models_ml")


def inferir(args: argparse.Namespace) -> int:
    cfg = ConfigAmostragem(
        cadeias=args.cadeias,
        aquecimento=args.aquecimento,
        amostras=args.amostras,
        semente=args.semente,
    )
    secoes = ler_secoes(args.entrada, args.ano, args.cargo, args.uf)
    pareadas, auditoria = parear_secoes(secoes, args.uf)
    log.info("auditoria %s: %s", args.uf, auditoria.como_dict())
    verificar_descarte(auditoria)
    m = montar_matrizes(pareadas)

    grupos = agrupar(m.municipios, m.zonas, args.max_secoes)
    resultados = []
    for g in np.unique(grupos):
        parte = subconjunto(m, grupos == g)
        log.info("%s grupo %d: %d secoes", args.uf, g, len(parte.n))
        resultados.append(ajustar(parte, cfg))
    resultado = combinar(resultados)

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    amostras_para_tabela(resultado, args.uf).write_parquet(
        saida / f"amostras_{args.uf}.parquet", compression="zstd"
    )
    meta = {
        "abrangencia": args.uf,
        "pesos": resultado.pesos.tolist(),
        "destino_total": m.contagens_destino.sum(axis=0).tolist(),
        "rhat_max": resultado.rhat_max,
        "ess_min": resultado.ess_min,
        "grupos": len(resultados),
        "config": cfg.__dict__,
        "auditoria": auditoria.como_dict(),
    }
    (saida / f"meta_{args.uf}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return 0


def _carregar_parcial(pasta: Path, uf: str) -> tuple[ResultadoEI, dict[str, object]]:
    meta = json.loads((pasta / f"meta_{uf}.json").read_text(encoding="utf-8"))
    tabela = pl.read_parquet(pasta / f"amostras_{uf}.parquet")
    resultado = tabela_para_amostras(
        tabela, np.array(meta["pesos"]), float(meta["rhat_max"]), float(meta["ess_min"])
    )
    return resultado, meta


def agregar(args: argparse.Namespace) -> int:
    pasta = Path(args.parciais)
    ufs = sorted(p.stem.removeprefix("meta_") for p in pasta.glob("meta_*.json"))
    if not ufs:
        raise FileNotFoundError(f"nenhum parcial em {pasta}")

    resumos: list[pl.DataFrame] = []
    auditorias: list[dict[str, object]] = []
    relatorios: list[Relatorio] = []
    parciais: list[ResultadoEI] = []
    destino_brasil = np.zeros(5)
    cfg = ConfigAmostragem()

    def processar(resultado: ResultadoEI, abrangencia: str, destino: np.ndarray) -> None:
        media = np.nanmean(resultado.amostras, axis=0)
        rel = validar(abrangencia, media, resultado.rhat_max, resultado.pesos, destino)
        relatorios.append(rel)
        resumos.append(resumir(resultado, abrangencia, cfg, rel.status))

    for uf in ufs:
        resultado, meta = _carregar_parcial(pasta, uf)
        cfg = ConfigAmostragem(**meta["config"])  # type: ignore[arg-type]
        destino = np.array(meta["destino_total"])
        destino_brasil += destino
        parciais.append(resultado)
        auditorias.append(meta["auditoria"])  # type: ignore[arg-type]
        processar(resultado, uf, destino)
    processar(combinar(parciais), "BR", destino_brasil)

    for rel in relatorios:
        for msg in rel.erros:
            log.error("%s: %s", rel.abrangencia, msg)
        for msg in rel.alertas:
            log.warning("%s: %s", rel.abrangencia, msg)

    destino_gold = Path(args.gold)
    particao = f"ano={args.ano}/cargo={args.cargo}"
    transicao = destino_gold / "fct_transicao_estimada" / particao / "part-0.parquet"
    auditoria = destino_gold / "fct_inferencia_auditoria" / particao / "part-0.parquet"
    for caminho in (transicao, auditoria):
        caminho.parent.mkdir(parents=True, exist_ok=True)
    pl.concat(resumos).write_parquet(transicao, compression="zstd")
    pl.DataFrame(auditorias).write_parquet(auditoria, compression="zstd")

    status = {r.status for r in relatorios}
    if REPROVADO in status:
        return 2
    if REVISAO in status and not args.aceitar_revisao:
        return 3
    log.info("matriz %s", APROVADO)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m models_ml")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("inferir")
    p.add_argument("--ano", type=int, required=True)
    p.add_argument("--cargo", required=True)
    p.add_argument("--uf", required=True)
    p.add_argument("--entrada", required=True, help="pasta ou URL base da Gold")
    p.add_argument("--saida", required=True)
    p.add_argument("--max-secoes", type=int, default=SECOES_POR_GRUPO)
    p.add_argument("--cadeias", type=int, default=4)
    p.add_argument("--aquecimento", type=int, default=2000)
    p.add_argument("--amostras", type=int, default=2000)
    p.add_argument("--semente", type=int, default=ConfigAmostragem.semente)

    a = sub.add_parser("agregar")
    a.add_argument("--ano", type=int, required=True)
    a.add_argument("--cargo", required=True)
    a.add_argument("--parciais", required=True)
    a.add_argument("--gold", required=True)
    a.add_argument("--aceitar-revisao", action="store_true", help="apos revisao manual")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parser().parse_args(argv)
    return inferir(args) if args.comando == "inferir" else agregar(args)

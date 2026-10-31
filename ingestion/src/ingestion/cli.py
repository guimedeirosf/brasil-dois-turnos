"""Ponto de entrada: python -m ingestion <comando> ...

Exemplos:
    python -m ingestion tse --ano 2026 --cargo presidente
    python -m ingestion tse --ano 2026 --cargo presidente --ufs RR AP
    python -m ingestion bcb --desde 1989-01
    python -m ingestion sidra --tabela pib_municipal
    python -m ingestion diretorios
    python -m ingestion exportar-gold
    python -m ingestion publicar-gold --run-id 123
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, date, datetime

from ingestion.config import SIDRA_TABELAS, TSE_CARGOS, UF_EXTERIOR, UFS, Config
from ingestion.gold import exportar_gold
from ingestion.http import ClienteHttp
from ingestion.manifest import Manifesto
from ingestion.sources.base import Source
from ingestion.sources.bcb_sgs import BcbSource
from ingestion.sources.diretorios import DiretoriosSource
from ingestion.sources.ibge_sidra import SidraSource
from ingestion.sources.tse import TseSource
from ingestion.storage import publicar_gold


def _mes(valor: str) -> date:
    return datetime.strptime(valor, "%Y-%m").date()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ingestion")
    parser.add_argument("--forcar", action="store_true", help="recarrega mesmo sem mudanca")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="comando", required=True)

    tse = sub.add_parser("tse", help="votacao, detalhe e candidatos de uma eleicao")
    tse.add_argument("--ano", type=int, required=True)
    tse.add_argument("--cargo", choices=sorted(TSE_CARGOS), required=True)
    tse.add_argument("--ufs", nargs="*", choices=(*UFS, UF_EXTERIOR), help="amostra de UFs")

    bcb = sub.add_parser("bcb", help="series mensais do BCB SGS")
    bcb.add_argument("--desde", type=_mes, default=date(1989, 1, 1), help="AAAA-MM")

    sidra = sub.add_parser("sidra", help="tabelas do IBGE SIDRA")
    sidra.add_argument("--tabela", choices=sorted(SIDRA_TABELAS), required=True)

    sub.add_parser("diretorios", help="municipios IBGE e de-para TSE")
    sub.add_parser("exportar-gold", help="warehouse -> data/gold (Parquet + manifesto)")

    publicar = sub.add_parser("publicar-gold", help="data/gold -> R2 (atomico)")
    publicar.add_argument("--run-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = Config.from_env()

    if args.comando == "exportar-gold":
        for tabela in exportar_gold(cfg):
            logging.info("exportada: %s", tabela)
        return 0
    if args.comando == "publicar-gold":
        # Prefixo de data deixa as pastas de staging em ordem cronologica
        carimbo = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        publicar_gold(cfg, f"{carimbo}-{args.run_id}")
        return 0

    http = ClienteHttp(tentativas=cfg.tentativas, timeout_s=cfg.timeout_s)
    manifesto = Manifesto(cfg.manifesto)
    fonte: Source
    if args.comando == "tse":
        ufs = tuple(args.ufs) if args.ufs else None
        fonte = TseSource(cfg, http, manifesto, args.ano, args.cargo, ufs)
    elif args.comando == "bcb":
        fonte = BcbSource(cfg, http, manifesto, args.desde)
    elif args.comando == "sidra":
        fonte = SidraSource(cfg, http, manifesto, args.tabela)
    else:
        fonte = DiretoriosSource(cfg, http, manifesto)
    try:
        cargas = fonte.run(forcar=args.forcar)
    finally:
        http.close()
    logging.info("%d particoes carregadas", len(cargas))
    return 0

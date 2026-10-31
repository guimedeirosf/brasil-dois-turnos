"""Gravacao da Bronze (local) e publicacao atomica da Gold no R2 (API S3)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import polars as pl

from ingestion.config import Config

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

log = logging.getLogger(__name__)

COLUNAS_AUDITORIA = ("_fonte", "_particao", "_carregado_em", "_hash_arquivo")
VERSOES_MANTIDAS = 2


def caminho_bronze(bronze_dir: Path, fonte: str, particao: dict[str, str]) -> Path:
    """bronze/<fonte>/<chave=valor>/.../part-0.parquet (estilo hive)."""
    pasta = bronze_dir / fonte
    for chave, valor in particao.items():
        pasta = pasta / f"{chave}={valor}"
    return pasta / "part-0.parquet"


def gravar_bronze(
    df: pl.DataFrame,
    bronze_dir: Path,
    fonte: str,
    particao: dict[str, str],
    hash_arquivo: str,
) -> Path:
    """Grava uma particao da Bronze substituindo a anterior (idempotente).

    Todas as colunas de origem viram texto; so as colunas de auditoria sao adicionadas.
    """
    destino = caminho_bronze(bronze_dir, fonte, particao)
    destino.parent.mkdir(parents=True, exist_ok=True)
    rotulo = "/".join(f"{k}={v}" for k, v in particao.items())
    df = df.select(pl.all().cast(pl.Utf8)).with_columns(
        pl.lit(fonte).alias("_fonte"),
        pl.lit(rotulo).alias("_particao"),
        pl.lit(datetime.now(UTC).isoformat(timespec="seconds")).alias("_carregado_em"),
        pl.lit(hash_arquivo).alias("_hash_arquivo"),
    )
    temporario = destino.with_suffix(".tmp")
    df.write_parquet(temporario, compression="zstd")
    temporario.replace(destino)
    return destino


def sha256_arquivo(caminho: Path) -> str:
    sha = hashlib.sha256()
    with caminho.open("rb") as arq:
        for bloco in iter(lambda: arq.read(1 << 20), b""):
            sha.update(bloco)
    return sha.hexdigest()


# --- R2 ------------------------------------------------------------------------------


def cliente_r2(cfg: Config) -> S3Client:
    import boto3

    if not (cfg.r2_account_id and cfg.r2_access_key_id and cfg.r2_secret_access_key):
        raise RuntimeError("defina R2_ACCOUNT_ID, R2_ACCESS_KEY_ID e R2_SECRET_ACCESS_KEY")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{cfg.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=cfg.r2_access_key_id,
        aws_secret_access_key=cfg.r2_secret_access_key,
        region_name="auto",
    )


def _tipo_conteudo(nome: str) -> str:
    return "application/json" if nome.endswith(".json") else "application/vnd.apache.parquet"


def publicar_gold(cfg: Config, run_id: str, s3: S3Client | None = None) -> dict[str, Any]:
    """Publicacao atomica: staging -> validacao -> copia para gold/ -> manifesto por ultimo.

    As duas ultimas pastas de staging ficam guardadas para rollback.
    """
    if not cfg.r2_bucket:
        raise RuntimeError("defina R2_BUCKET")
    s3 = s3 or cliente_r2(cfg)
    bucket = cfg.r2_bucket
    local_manifesto = cfg.gold_dir / "_manifest.json"
    manifesto = json.loads(local_manifesto.read_text(encoding="utf-8"))
    arquivos = sorted(p for p in cfg.gold_dir.rglob("*.parquet"))
    prefixo_staging = f"gold/_staging/{run_id}/"

    for arq in arquivos:
        chave = prefixo_staging + arq.relative_to(cfg.gold_dir).as_posix()
        s3.upload_file(str(arq), bucket, chave, ExtraArgs={"ContentType": _tipo_conteudo(arq.name)})

    # Validacao: tudo que foi enviado existe com o mesmo tamanho
    for arq in arquivos:
        chave = prefixo_staging + arq.relative_to(cfg.gold_dir).as_posix()
        remoto = s3.head_object(Bucket=bucket, Key=chave)
        if remoto["ContentLength"] != arq.stat().st_size:
            raise RuntimeError(f"tamanho divergente no staging: {chave}")

    cache = "public, max-age=86400"
    for arq in arquivos:
        relativo = arq.relative_to(cfg.gold_dir).as_posix()
        s3.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": prefixo_staging + relativo},
            Key=f"gold/{relativo}",
            CacheControl=cache,
            ContentType=_tipo_conteudo(relativo),
            MetadataDirective="REPLACE",
        )

    manifesto = mesclar_manifestos(_manifesto_remoto(s3, bucket), manifesto)
    manifesto["run_id"] = run_id
    corpo = json.dumps(manifesto, ensure_ascii=False, indent=2).encode()
    s3.put_object(Bucket=bucket, Key=prefixo_staging + "_manifest.json", Body=corpo)
    s3.put_object(
        Bucket=bucket,
        Key="gold/_manifest.json",
        Body=corpo,
        ContentType="application/json",
        CacheControl="public, max-age=300",
    )
    _podar_staging(s3, bucket)
    log.info("gold publicada: %d arquivos (run %s)", len(arquivos), run_id)
    return dict(manifesto)


def _manifesto_remoto(s3: S3Client, bucket: str) -> dict[str, Any]:
    try:
        corpo = s3.get_object(Bucket=bucket, Key="gold/_manifest.json")["Body"].read()
    except s3.exceptions.NoSuchKey:
        return {"tabelas": {}}
    return dict(json.loads(corpo))


def mesclar_manifestos(remoto: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    """Cada workflow publica so parte da Gold: mantem os arquivos remotos e sobrepoe os locais."""
    tabelas: dict[str, Any] = {}
    for nome in sorted({*remoto.get("tabelas", {}), *local.get("tabelas", {})}):
        arquivos = {
            a["caminho"]: a for a in remoto.get("tabelas", {}).get(nome, {}).get("arquivos", [])
        }
        arquivos.update(
            {a["caminho"]: a for a in local.get("tabelas", {}).get(nome, {}).get("arquivos", [])}
        )
        lista = [arquivos[c] for c in sorted(arquivos)]
        tabelas[nome] = {"linhas": sum(a["linhas"] for a in lista), "arquivos": lista}
    return {**local, "tabelas": tabelas}


def _podar_staging(s3: S3Client, bucket: str) -> None:
    pastas: list[str] = []
    paginador = s3.get_paginator("list_objects_v2")
    for pagina in paginador.paginate(Bucket=bucket, Prefix="gold/_staging/", Delimiter="/"):
        pastas.extend(p["Prefix"] for p in pagina.get("CommonPrefixes", []))
    for pasta in sorted(pastas)[:-VERSOES_MANTIDAS]:
        for pagina in paginador.paginate(Bucket=bucket, Prefix=pasta):
            objetos = [{"Key": o["Key"]} for o in pagina.get("Contents", [])]
            if objetos:
                s3.delete_objects(Bucket=bucket, Delete={"Objects": objetos})  # type: ignore[typeddict-item]

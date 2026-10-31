from __future__ import annotations

import dataclasses
import io
import json
from pathlib import Path
from typing import Any

import pytest

from ingestion import cli
from ingestion.config import Config
from ingestion.storage import mesclar_manifestos, publicar_gold


class S3Falso:
    """Bucket em memoria com o subconjunto da API S3 usado na publicacao."""

    class exceptions:
        class NoSuchKey(Exception):
            pass

    def __init__(self) -> None:
        self.objetos: dict[str, bytes] = {}
        self.ordem: list[str] = []

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objetos:
            raise self.exceptions.NoSuchKey(Key)
        return {"Body": io.BytesIO(self.objetos[Key])}

    def upload_file(self, origem: str, bucket: str, chave: str, ExtraArgs: Any = None) -> None:
        self._gravar(chave, Path(origem).read_bytes())

    def head_object(self, Bucket: str, Key: str) -> dict[str, int]:
        return {"ContentLength": len(self.objetos[Key])}

    def copy_object(self, Bucket: str, CopySource: dict[str, str], Key: str, **_: Any) -> None:
        self._gravar(Key, self.objetos[CopySource["Key"]])

    def put_object(self, Bucket: str, Key: str, Body: bytes, **_: Any) -> None:
        self._gravar(Key, Body)

    def get_paginator(self, _: str) -> S3Falso:
        return self

    def paginate(
        self, Bucket: str, Prefix: str, Delimiter: str | None = None
    ) -> list[dict[str, Any]]:
        chaves = [k for k in self.objetos if k.startswith(Prefix)]
        if Delimiter:
            pastas = sorted(
                {Prefix + k[len(Prefix) :].split(Delimiter)[0] + Delimiter for k in chaves}
            )
            return [{"CommonPrefixes": [{"Prefix": p} for p in pastas]}]
        return [{"Contents": [{"Key": k} for k in chaves]}]

    def delete_objects(self, Bucket: str, Delete: dict[str, list[dict[str, str]]]) -> None:
        for objeto in Delete["Objects"]:
            del self.objetos[objeto["Key"]]

    def _gravar(self, chave: str, corpo: bytes) -> None:
        self.objetos[chave] = corpo
        self.ordem.append(chave)


def _arquivo(caminho: str, linhas: int) -> dict[str, Any]:
    return {"caminho": caminho, "linhas": linhas}


def _gold(cfg: Config) -> None:
    arquivo = cfg.gold_dir / "srv_x/ano=2026/cargo=presidente/part-0.parquet"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_bytes(b"PAR1-falso")
    local = {
        "tabelas": {
            "srv_x": {"arquivos": [_arquivo("srv_x/ano=2026/cargo=presidente/part-0.parquet", 5)]}
        }
    }
    (cfg.gold_dir / "_manifest.json").write_text(json.dumps(local), encoding="utf-8")


def test_mescla_manifesto_remoto_sem_perder_outras_eleicoes(cfg: Config) -> None:
    cfg = dataclasses.replace(cfg, r2_bucket="bucket")
    _gold(cfg)
    s3 = S3Falso()
    remoto = {
        "tabelas": {
            "srv_x": {"arquivos": [_arquivo("srv_x/ano=2022/cargo=presidente/part-0.parquet", 7),
                                   _arquivo("srv_x/ano=2026/cargo=presidente/part-0.parquet", 1)]},
            "fct_macro_mes": {"arquivos": [_arquivo("fct_macro_mes/part-0.parquet", 400)]},
        }
    }  # fmt: skip
    s3.objetos["gold/_manifest.json"] = json.dumps(remoto).encode()

    publicado = publicar_gold(cfg, "20261030T000000-1", s3)  # type: ignore[arg-type]

    assert publicado["tabelas"]["srv_x"]["linhas"] == 7 + 5
    assert publicado["tabelas"]["fct_macro_mes"]["linhas"] == 400


def test_mesclar_manifestos_local_prevalece() -> None:
    remoto = {"tabelas": {"t": {"arquivos": [_arquivo("t/a", 1), _arquivo("t/b", 2)]}}}
    local = {"gerado_em": "agora", "tabelas": {"t": {"arquivos": [_arquivo("t/b", 9)]}}}
    mesclado = mesclar_manifestos(remoto, local)
    assert mesclado["gerado_em"] == "agora"
    assert mesclado["tabelas"]["t"] == {
        "linhas": 10,
        "arquivos": [_arquivo("t/a", 1), _arquivo("t/b", 9)],
    }


def test_publicacao_atomica_manifesto_por_ultimo(cfg: Config) -> None:
    cfg = dataclasses.replace(cfg, r2_bucket="bucket")
    _gold(cfg)
    s3 = S3Falso()

    publicar_gold(cfg, "20261030T000000-1", s3)  # type: ignore[arg-type]

    assert s3.objetos["gold/srv_x/ano=2026/cargo=presidente/part-0.parquet"] == b"PAR1-falso"
    assert s3.ordem[-1] == "gold/_manifest.json"
    assert json.loads(s3.objetos["gold/_manifest.json"])["run_id"] == "20261030T000000-1"


def test_mantem_so_duas_versoes_de_staging(cfg: Config) -> None:
    cfg = dataclasses.replace(cfg, r2_bucket="bucket")
    _gold(cfg)
    s3 = S3Falso()
    for run in ("20260101T000000-1", "20260201T000000-2", "20260301T000000-3"):
        publicar_gold(cfg, run, s3)  # type: ignore[arg-type]

    staging = {k.split("/")[2] for k in s3.objetos if k.startswith("gold/_staging/")}
    assert staging == {"20260201T000000-2", "20260301T000000-3"}


def test_publicacao_sem_bucket_falha(cfg: Config) -> None:
    with pytest.raises(RuntimeError, match="R2_BUCKET"):
        publicar_gold(cfg, "x", S3Falso())  # type: ignore[arg-type]


def test_cli_exige_comando() -> None:
    with pytest.raises(SystemExit):
        cli.main([])


def test_cli_tse_valida_cargo() -> None:
    with pytest.raises(SystemExit):
        cli.main(["tse", "--ano", "2026", "--cargo", "vereador"])


def test_cli_exportar_gold(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[Config] = []
    monkeypatch.setattr(cli.Config, "from_env", classmethod(lambda _: cfg))
    monkeypatch.setattr(cli, "exportar_gold", lambda c: chamadas.append(c) or ["fct_x"])
    assert cli.main(["exportar-gold"]) == 0
    assert chamadas == [cfg]


def test_cli_roda_fonte(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    rodadas: list[str] = []
    monkeypatch.setattr(cli.Config, "from_env", classmethod(lambda _: cfg))
    monkeypatch.setattr(cli.TseSource, "run", lambda self, forcar: rodadas.append(self.cargo) or [])
    assert cli.main(["tse", "--ano", "2026", "--cargo", "presidente", "--ufs", "RR"]) == 0
    assert rodadas == ["presidente"]

from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.config import Config
from ingestion.http import ClienteHttp
from ingestion.manifest import Manifesto


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    return Config(
        data_dir=tmp_path,
        bronze_dir=tmp_path / "bronze",
        gold_dir=tmp_path / "gold",
        warehouse=tmp_path / "warehouse.duckdb",
        manifesto=tmp_path / "manifest" / "bronze.json",
        ambiente="ci",
    )


@pytest.fixture
def http() -> ClienteHttp:
    cliente = ClienteHttp(tentativas=3, timeout_s=5, espera_base_s=0)
    yield cliente
    cliente.close()


@pytest.fixture
def manifesto(cfg: Config) -> Manifesto:
    return Manifesto(cfg.manifesto)

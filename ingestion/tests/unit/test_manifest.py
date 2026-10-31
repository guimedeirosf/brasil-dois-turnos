from __future__ import annotations

import json
from pathlib import Path

from ingestion.manifest import Manifesto


def test_registro_e_idempotente(tmp_path: Path) -> None:
    caminho = tmp_path / "m.json"
    m = Manifesto(caminho)
    m.registrar("tse", "votacao/ano=2026", "u", "abc", 10, "sig1")
    m.registrar("tse", "votacao/ano=2026", "u", "abc", 10, "sig1")

    conteudo = json.loads(caminho.read_text(encoding="utf-8"))
    assert len(conteudo) == 1
    assert conteudo[0]["linhas"] == 10


def test_esta_atual_compara_assinatura(tmp_path: Path) -> None:
    m = Manifesto(tmp_path / "m.json")
    assert not m.esta_atual("tse", "p", "sig1")
    m.registrar("tse", "p", "u", "abc", 1, "sig1")
    assert m.esta_atual("tse", "p", "sig1")
    assert not m.esta_atual("tse", "p", "sig2")


def test_recarrega_do_disco_em_ordem(tmp_path: Path) -> None:
    caminho = tmp_path / "m.json"
    m = Manifesto(caminho)
    m.registrar("tse", "b", "u", "h2", 2, "s")
    m.registrar("bcb", "a", "u", "h1", 1, "s")

    recarregado = Manifesto(caminho)
    assert [c.fonte for c in recarregado.cargas()] == ["bcb", "tse"]
    ultima = recarregado.ultima("tse", "b")
    assert ultima is not None and ultima.sha256 == "h2"

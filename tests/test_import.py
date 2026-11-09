"""Valida a disponibilidade do pacote instalado."""

import emporio_agent


def test_package_import():
    assert emporio_agent.__name__ == "emporio_agent"

"""Caminhos do repositório e do conjunto de dados de exemplo."""

from __future__ import annotations

import os
from pathlib import Path

PACOTE = Path(__file__).resolve().parent


def diretorio_raiz() -> Path:
    bruto = os.environ.get("ORQUESTRADOR_RAIZ")
    if bruto:
        return Path(bruto)
    return PACOTE.parents[1]


def diretorio_dados() -> Path:
    bruto = os.environ.get("ORQUESTRADOR_DATA")
    if bruto:
        return Path(bruto)
    return PACOTE / "dados_exemplo"


def diretorio_servidores() -> Path:
    return diretorio_raiz() / "mcp_servers"

"""Log JSON por etapa. Langfuse só entra se as chaves e o pacote existirem."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("orquestrador")

_langfuse: Any = None
_langfuse_estado = "pendente"


def configurar_log() -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def _cliente_langfuse() -> Any:
    global _langfuse, _langfuse_estado
    if _langfuse_estado != "pendente":
        return _langfuse
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        _langfuse_estado = "desligado"
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        _langfuse_estado = "pacote_ausente"
        logger.info(
            json.dumps(
                {"etapa": "langfuse", "detalhe": "chaves presentes e pacote ausente"},
                ensure_ascii=False,
            )
        )
        return None
    try:
        _langfuse = Langfuse()
        _langfuse_estado = "ativo"
    except Exception as exc:  # noqa: BLE001
        _langfuse_estado = "falhou"
        logger.info(
            json.dumps(
                {"etapa": "langfuse", "detalhe": f"cliente nao iniciou: {exc}"},
                ensure_ascii=False,
            )
        )
        _langfuse = None
    return _langfuse


def emitir(etapa: str, **detalhe: Any) -> dict[str, Any]:
    configurar_log()
    evento: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "etapa": etapa,
    }
    evento.update(detalhe)
    logger.info(json.dumps(evento, ensure_ascii=False, default=str))
    cliente = _cliente_langfuse()
    if cliente is not None:
        try:
            cliente.trace(name=etapa, metadata=evento)
        except Exception:
            global _langfuse_estado
            _langfuse_estado = "falhou"
    return evento

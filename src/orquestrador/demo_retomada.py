"""Demonstração de retomada: o nó de notas falha e o mesmo checkpoint conclui."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from orquestrador.grafo import compilar, executar
from orquestrador.nos import FalhaControlada

PERGUNTA = (
    "Quais compromissos tenho em 2026-11-21 e o que as notas dizem sobre guardrails?"
)


def demonstrar(caminho: Path | None = None) -> dict:
    proprio = caminho is None
    if caminho is None:
        pasta = tempfile.mkdtemp()
        caminho = Path(pasta) / "checkpoint.sqlite"
    thread_id = "demo-retomada"
    os.environ["ORQUESTRADOR_FALHA_NO"] = "notas"
    config = {"configurable": {"thread_id": thread_id}}
    with SqliteSaver.from_conn_string(str(caminho)) as saver:
        try:
            executar(PERGUNTA, thread_id=thread_id, checkpointer=saver)
            raise RuntimeError("a falha injetada não aconteceu")
        except FalhaControlada as exc:
            falha = str(exc)
        estado = compilar(saver).get_state(config)
        proximo = list(estado.next)
        parcial = [
            item["texto"] for item in estado.values.get("resultados", []) if item["agente"] == "agenda"
        ]
    os.environ["ORQUESTRADOR_FALHA_NO"] = ""
    with SqliteSaver.from_conn_string(str(caminho)) as saver:
        final = executar(None, thread_id=thread_id, checkpointer=saver, retomar=True)
    relatorio = {
        "thread_id": thread_id,
        "checkpoint": str(caminho),
        "falha": falha,
        "proximo_no_momento_da_falha": proximo,
        "parcial_agenda": parcial,
        "resposta": final.resposta,
        "agentes": final.agentes,
    }
    if proprio:
        print(f"thread_id: {thread_id}")
        print(f"falha: {falha}")
        print(f"próximo nó gravado no checkpoint: {proximo}")
        print(f"parcial da agenda: {parcial}")
        print(f"resposta depois da retomada:\n{final.resposta}")
    return relatorio

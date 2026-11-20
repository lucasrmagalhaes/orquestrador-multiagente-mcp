"""Grafo do supervisor com checkpoint."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from orquestrador.nos import fazer_no_agente, no_supervisor


class Estado(TypedDict, total=False):
    pergunta: str
    plano: list
    resultados: list
    resposta: str
    iteracao: int
    bloqueios: list
    trace: list
    ferramentas_executadas: list
    ferramentas_recusadas: list
    proximo: str
    recusa: bool


@dataclass
class Resultado:
    resposta: str
    agentes: list[str]
    bloqueios: list[dict]
    trace: list[dict]
    ferramentas_executadas: list[str]
    ferramentas_recusadas: list[str]
    recusa: bool
    thread_id: str
    iteracao: int = 0
    extras: dict[str, Any] = field(default_factory=dict)


def compilar(checkpointer: Any):
    grafo = StateGraph(Estado)
    grafo.add_node("supervisor", no_supervisor)
    for agente in ("agenda", "notas", "issues"):
        grafo.add_node(agente, fazer_no_agente(agente))
        grafo.add_edge(agente, "supervisor")
    grafo.add_edge(START, "supervisor")
    grafo.add_conditional_edges(
        "supervisor",
        lambda state: state.get("proximo") or "fim",
        {"agenda": "agenda", "notas": "notas", "issues": "issues", "fim": END},
    )
    return grafo.compile(checkpointer=checkpointer)


def estado_inicial(pergunta: str) -> dict:
    return {
        "pergunta": pergunta,
        "plano": [],
        "resultados": [],
        "resposta": "",
        "iteracao": 0,
        "bloqueios": [],
        "trace": [],
        "ferramentas_executadas": [],
        "ferramentas_recusadas": [],
        "proximo": "",
        "recusa": False,
    }


def executar(
    pergunta: str | None = None,
    *,
    thread_id: str | None = None,
    checkpointer: Any = None,
    retomar: bool = False,
) -> Resultado:
    saver = checkpointer if checkpointer is not None else MemorySaver()
    app = compilar(saver)
    identificador = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": identificador}, "recursion_limit": 25}
    if retomar:
        final = app.invoke(None, config)
    else:
        final = app.invoke(estado_inicial(pergunta or ""), config)
    resultados = final.get("resultados", [])
    return Resultado(
        resposta=final.get("resposta", ""),
        agentes=[item["agente"] for item in resultados],
        bloqueios=list(final.get("bloqueios", [])),
        trace=list(final.get("trace", [])),
        ferramentas_executadas=list(final.get("ferramentas_executadas", [])),
        ferramentas_recusadas=list(final.get("ferramentas_recusadas", [])),
        recusa=bool(final.get("recusa", False)),
        thread_id=identificador,
        iteracao=int(final.get("iteracao", 0)),
    )

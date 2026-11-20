"""Nós do grafo: supervisor e três agentes especializados."""

from __future__ import annotations

import os
import re
from typing import Any

from langchain_core.runnables import RunnableConfig

from orquestrador.constantes import FERRAMENTAS_LEITURA
from orquestrador.guardrails import (
    analisar_pedido_usuario,
    filtrar_saida,
    sanitizar_conteudo_externo,
)
from orquestrador.llm import (
    escolher_leitura_real,
    planejar,
    provedor_atual,
    responder_especialista,
    resumo_extrativo,
)
from orquestrador.mcp_cliente import chamar
from orquestrador.politica import avaliar_ferramenta, passo_dentro_do_limite
from orquestrador.tracing import emitir


class FalhaControlada(RuntimeError):
    """Interrupção proposital para a demonstração de checkpoint."""


def _thread(config: RunnableConfig) -> str:
    return str(config.get("configurable", {}).get("thread_id", ""))


def escolher_leitura(agente: str, pergunta: str) -> tuple[str, dict[str, str]]:
    permitidas = sorted(FERRAMENTAS_LEITURA[agente])
    if provedor_atual() != "mock":
        nome, argumentos = escolher_leitura_real(agente, pergunta, permitidas)
        if nome:
            return nome, argumentos
    if agente == "agenda":
        data = re.search(r"\d{4}-\d{2}-\d{2}", pergunta)
        if data:
            return "listar_compromissos", {"dia": data.group(0)}
        return "buscar_compromisso", {"termo": pergunta}
    if agente == "notas":
        return "buscar_notas", {"consulta": pergunta}
    identificador = re.search(r"\b(?:GH|AI)-\d+\b", pergunta, re.IGNORECASE)
    if identificador:
        return "ler_issue", {"identificador": identificador.group(0)}
    return "listar_issues", {"consulta": pergunta}


def sintetizar(state: dict) -> str:
    partes = [f"{item['agente']}: {item['texto']}" for item in state.get("resultados", [])]
    return "\n".join(partes)


def no_supervisor(state: dict, config: RunnableConfig) -> dict[str, Any]:
    thread_id = _thread(config)
    iteracao = int(state.get("iteracao", 0)) + 1
    trace = list(state.get("trace", []))
    bloqueios = list(state.get("bloqueios", []))
    base = {
        "iteracao": iteracao,
        "trace": trace,
        "bloqueios": bloqueios,
        "plano": list(state.get("plano", [])),
        "recusa": bool(state.get("recusa", False)),
    }
    if not passo_dentro_do_limite(iteracao):
        resposta = state.get("resposta") or sintetizar(state) or (
            "Limite de passos do supervisor atingido."
        )
        trace.append(emitir("supervisor", thread_id=thread_id, decisao="limite", iteracao=iteracao))
        return {**base, "proximo": "fim", "resposta": resposta}

    if not state.get("resultados") and not state.get("plano") and not state.get("recusa"):
        analise = analisar_pedido_usuario(state["pergunta"])
        if analise.recusar:
            bloqueios.append(
                {
                    "camada": analise.camada,
                    "motivo": analise.motivo,
                    "padroes": analise.padroes,
                }
            )
            if analise.camada == "politica_autonomia":
                resposta = (
                    "Pedido recusado pelo limite de autonomia. "
                    "Eu leio agenda, notas e issues e recuso apagar, enviar ou executar comandos."
                )
            else:
                resposta = (
                    "Pedido recusado pelos guardrails. "
                    "O texto tem cara de instrução para furar a política do assistente."
                )
            trace.append(
                emitir(
                    "supervisor",
                    thread_id=thread_id,
                    decisao="recusa",
                    camada=analise.camada,
                    iteracao=iteracao,
                )
            )
            return {**base, "proximo": "fim", "resposta": resposta, "recusa": True, "plano": []}
        plano = planejar(state["pergunta"])
        if not plano:
            trace.append(
                emitir("supervisor", thread_id=thread_id, decisao="sem_agente", iteracao=iteracao)
            )
            return {
                **base,
                "proximo": "fim",
                "plano": [],
                "resposta": (
                    "Não encontrei um pedido para a agenda, as notas ou as issues de exemplo."
                ),
            }
        trace.append(
            emitir(
                "supervisor",
                thread_id=thread_id,
                decisao="delegar",
                agentes=plano,
                iteracao=iteracao,
            )
        )
        return {**base, "plano": plano[1:], "proximo": plano[0]}

    if state.get("plano"):
        proximo = state["plano"][0]
        trace.append(
            emitir(
                "supervisor",
                thread_id=thread_id,
                decisao="delegar",
                agente=proximo,
                iteracao=iteracao,
            )
        )
        return {**base, "plano": list(state["plano"][1:]), "proximo": proximo}

    resposta = sintetizar(state)
    trace.append(emitir("supervisor", thread_id=thread_id, decisao="concluir", iteracao=iteracao))
    return {**base, "proximo": "fim", "resposta": resposta}


def fazer_no_agente(agente: str):
    def nodo(state: dict, config: RunnableConfig) -> dict[str, Any]:
        if os.environ.get("ORQUESTRADOR_FALHA_NO") == agente:
            raise FalhaControlada(
                f"falha injetada no agente de {agente} para demonstrar a retomada"
            )
        thread_id = _thread(config)
        trace = list(state.get("trace", []))
        bloqueios = list(state.get("bloqueios", []))
        executadas = list(state.get("ferramentas_executadas", []))
        recusadas = list(state.get("ferramentas_recusadas", []))
        resultados = list(state.get("resultados", []))
        nome, argumentos = escolher_leitura(agente, state["pergunta"])
        decisao = avaliar_ferramenta(agente, nome, len(executadas))
        texto = ""
        if not decisao.permitido:
            recusadas.append(nome)
            bloqueios.append(
                {"agente": agente, "camada": "politica", "ferramenta": nome, "motivo": decisao.motivo}
            )
            texto = "Ferramenta de leitura recusada pela política de autonomia."
        else:
            bruto = chamar(agente, nome, argumentos)
            executadas.append(nome)
            sanitizado = sanitizar_conteudo_externo(bruto, origem=agente)
            if sanitizado.detectado:
                bloqueios.append(
                    {
                        "agente": agente,
                        "camada": "deteccao",
                        "padroes": sanitizado.padroes,
                    }
                )
            modelo = responder_especialista(agente, state["pergunta"], sanitizado.texto)
            if modelo.ferramenta:
                extra = avaliar_ferramenta(agente, modelo.ferramenta, len(executadas))
                if not extra.permitido:
                    recusadas.append(modelo.ferramenta)
                    bloqueios.append(
                        {
                            "agente": agente,
                            "camada": "politica",
                            "ferramenta": modelo.ferramenta,
                            "motivo": extra.motivo,
                        }
                    )
                else:
                    complemento = chamar(agente, modelo.ferramenta, modelo.argumentos or {})
                    executadas.append(modelo.ferramenta)
                    sanitizado = sanitizar_conteudo_externo(
                        bruto + "\n" + complemento, origem=agente
                    )
            texto, removeu = filtrar_saida(modelo.texto)
            if removeu:
                bloqueios.append({"agente": agente, "camada": "filtro_saida"})
                texto, _ = filtrar_saida(
                    "A resposta do modelo foi descartada porque incluía material interno. "
                    + resumo_extrativo(sanitizado.texto)
                )
            if modelo.ferramenta and modelo.ferramenta in recusadas:
                texto = f"{texto} A política recusou a ferramenta pedida."
        resultados.append({"agente": agente, "texto": texto})
        trace.append(
            emitir(
                agente,
                thread_id=thread_id,
                ferramenta=nome,
                bloqueios=len(bloqueios),
            )
        )
        return {
            "trace": trace,
            "bloqueios": bloqueios,
            "ferramentas_executadas": executadas,
            "ferramentas_recusadas": recusadas,
            "resultados": resultados,
        }

    nodo.__name__ = f"no_{agente}"
    return nodo

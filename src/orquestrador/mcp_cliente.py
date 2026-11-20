"""Cliente das ferramentas. stdio fala com os servidores MCP. processo usa o mesmo código."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from orquestrador.caminhos import diretorio_servidores
from orquestrador.ferramentas import FERRAMENTAS

_SERVIDORES = {
    "agenda": "agenda_server.py",
    "notas": "notas_server.py",
    "issues": "issues_server.py",
}


class FerramentaIndisponivel(RuntimeError):
    pass


def modo_mcp() -> str:
    return os.environ.get("ORQUESTRADOR_MCP", "stdio").strip().lower() or "stdio"


def chamar(agente: str, nome: str, argumentos: dict[str, str]) -> str:
    if nome not in FERRAMENTAS:
        raise FerramentaIndisponivel(nome)
    if modo_mcp() == "processo":
        return _chamar_processo(nome, argumentos)
    if modo_mcp() == "stdio":
        return asyncio.run(_chamar_stdio(agente, nome, argumentos))
    raise FerramentaIndisponivel(f"modo MCP desconhecido: {modo_mcp()}")


def _chamar_processo(nome: str, argumentos: dict[str, str]) -> str:
    funcao = FERRAMENTAS[nome]
    return str(funcao(**argumentos))


async def _chamar_stdio(agente: str, nome: str, argumentos: dict[str, str]) -> str:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    script = diretorio_servidores() / _SERVIDORES[agente]
    if not script.exists():
        raise FerramentaIndisponivel(f"servidor ausente: {script}")
    ambiente = os.environ.copy()
    raiz_src = str(script.resolve().parents[1] / "src")
    ambiente["PYTHONPATH"] = raiz_src + os.pathsep + ambiente.get("PYTHONPATH", "")
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(script)],
        env=ambiente,
    )
    async with stdio_client(params) as (leitura, escrita):
        async with ClientSession(leitura, escrita) as sessao:
            await sessao.initialize()
            resultado = await sessao.call_tool(nome, argumentos)
    if getattr(resultado, "is_error", False):
        raise FerramentaIndisponivel(_textos(resultado) or nome)
    return _textos(resultado)


def _textos(resultado: Any) -> str:
    partes = []
    for bloco in getattr(resultado, "content", []) or []:
        texto = getattr(bloco, "text", None)
        if texto:
            partes.append(texto)
    if partes:
        return "\n".join(partes)
    estruturado = getattr(resultado, "structured_content", None)
    if estruturado is not None:
        return json.dumps(estruturado, ensure_ascii=False)
    return ""

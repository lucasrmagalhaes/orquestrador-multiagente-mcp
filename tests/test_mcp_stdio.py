import asyncio
import os
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from orquestrador.caminhos import diretorio_servidores
from orquestrador.grafo import executar


def _chamar(script: str, nome: str, argumentos: dict) -> str:
    async def correr():
        ambiente = os.environ.copy()
        ambiente["PYTHONPATH"] = str(
            diretorio_servidores().resolve().parents[0] / "src"
        ) + os.pathsep + ambiente.get("PYTHONPATH", "")
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(diretorio_servidores() / script)],
            env=ambiente,
        )
        async with stdio_client(params) as (leitura, escrita):
            async with ClientSession(leitura, escrita) as sessao:
                await sessao.initialize()
                ferramentas = await sessao.list_tools()
                nomes = [ferramenta.name for ferramenta in ferramentas.tools]
                resultado = await sessao.call_tool(nome, argumentos)
        return nomes, "".join(bloco.text for bloco in resultado.content if getattr(bloco, "text", None))

    return asyncio.run(correr())


def test_tres_servidores_expoem_as_ferramentas_de_leitura():
    nomes, texto = _chamar("agenda_server.py", "listar_compromissos", {"dia": "2026-11-21"})
    assert "listar_compromissos" in nomes
    assert "Daily do time de plataforma" in texto

    nomes, texto = _chamar("notas_server.py", "buscar_notas", {"consulta": "guardrails"})
    assert "buscar_notas" in nomes
    assert "é dado" in texto

    nomes, texto = _chamar("issues_server.py", "ler_issue", {"identificador": "AI-22"})
    assert "ler_issue" in nomes
    assert "autonomia" in texto


def test_grafo_usa_stdio(monkeypatch):
    monkeypatch.setenv("ORQUESTRADOR_MCP", "stdio")
    resultado = executar("Quais compromissos tenho em 2026-11-21?")
    assert "Daily do time de plataforma" in resultado.resposta
    assert "listar_compromissos" in resultado.ferramentas_executadas

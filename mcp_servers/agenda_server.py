"""Servidor MCP da agenda de exemplo. Sem conta de calendário."""

from mcp.server.mcpserver import MCPServer

import orquestrador.ferramentas as ferramentas

server = MCPServer("agenda")


@server.tool(name="listar_compromissos")
def tool_listar_compromissos(dia: str) -> str:
    """Lista compromissos de exemplo de um dia no formato YYYY-MM-DD."""
    return ferramentas.listar_compromissos(dia)


@server.tool(name="buscar_compromisso")
def tool_buscar_compromisso(termo: str) -> str:
    """Busca compromissos de exemplo pelo título ou pelo local."""
    return ferramentas.buscar_compromisso(termo)


if __name__ == "__main__":
    server.run(transport="stdio")

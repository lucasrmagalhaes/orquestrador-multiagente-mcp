"""Servidor MCP das notas de exemplo e do retriever local."""

from mcp.server.mcpserver import MCPServer

import orquestrador.ferramentas as ferramentas

server = MCPServer("notas")


@server.tool(name="buscar_notas")
def tool_buscar_notas(consulta: str) -> str:
    """Recupera trechos das notas de exemplo por TF-IDF."""
    return ferramentas.buscar_notas(consulta)


@server.tool(name="listar_notas")
def tool_listar_notas() -> str:
    """Lista os arquivos de notas de exemplo."""
    return ferramentas.listar_notas()


if __name__ == "__main__":
    server.run(transport="stdio")

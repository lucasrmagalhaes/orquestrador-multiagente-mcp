"""Servidor MCP de issues de exemplo, no formato GitHub e Jira."""

from mcp.server.mcpserver import MCPServer

import orquestrador.ferramentas as ferramentas

server = MCPServer("issues")


@server.tool(name="listar_issues")
def tool_listar_issues(consulta: str) -> str:
    """Lista issues de exemplo do GitHub e do Jira a partir de uma consulta."""
    return ferramentas.listar_issues(consulta)


@server.tool(name="ler_issue")
def tool_ler_issue(identificador: str) -> str:
    """Lê uma issue de exemplo pelo id, como GH-101 ou AI-22."""
    return ferramentas.ler_issue(identificador)


if __name__ == "__main__":
    server.run(transport="stdio")

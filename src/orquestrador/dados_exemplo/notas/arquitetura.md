# Arquitetura do orquestrador

O supervisor recebe o pedido e delega para três agentes: agenda, notas e issues.
Cada agente fala com um servidor MCP próprio.
As notas passam por um índice local antes de chegar ao modelo.
O grafo é LangGraph, com um nó por papel.

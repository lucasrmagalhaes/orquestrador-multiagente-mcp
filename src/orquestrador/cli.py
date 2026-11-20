"""Linha de comando do orquestrador."""

from __future__ import annotations

import json
import sys

from orquestrador.redteam import executar_suite, frase_taxa, rodar_benignos, tabela_markdown
from orquestrador.tracing import configurar_log


def main(argv: list[str] | None = None) -> int:
    configurar_log()
    argumentos = list(sys.argv[1:] if argv is None else argv)
    if not argumentos or argumentos[0] in {"-h", "--help"}:
        print(
            "uso: orquestrador \"pedido\" | perguntar \"pedido\" | redteam | retomada | servir"
        )
        return 0 if argumentos else 2
    comando = argumentos[0]
    if comando == "redteam":
        relatorio = executar_suite()
        benignos = rodar_benignos()
        print(frase_taxa(relatorio))
        print(tabela_markdown(relatorio))
        print(
            "Pedidos benignos de controle: "
            f"{sum(1 for item in benignos if item['ok'])} de {len(benignos)}."
        )
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
        return 0 if all(item["ok"] for item in benignos) else 1
    if comando == "retomada":
        from orquestrador.demo_retomada import demonstrar

        demonstrar()
        return 0
    if comando == "servir":
        from orquestrador.servico import servir

        servir()
        return 0
    if comando == "perguntar":
        if len(argumentos) < 2:
            print("uso: orquestrador perguntar \"pedido\"", file=sys.stderr)
            return 2
        return _perguntar(" ".join(argumentos[1:]))
    return _perguntar(" ".join(argumentos))


def _perguntar(texto: str) -> int:
    from orquestrador.grafo import executar
    from orquestrador.llm import ChaveAusente

    try:
        resultado = executar(texto)
    except ChaveAusente as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(resultado.resposta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

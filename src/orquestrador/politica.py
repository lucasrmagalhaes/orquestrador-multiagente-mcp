"""Lista de ferramentas e teto de autonomia do supervisor."""

from __future__ import annotations

from dataclasses import dataclass

from orquestrador.constantes import (
    FERRAMENTAS_LEITURA,
    FERRAMENTAS_PROIBIDAS,
    LIMITE_FERRAMENTAS,
    LIMITE_PASSOS,
)


@dataclass
class DecisaoFerramenta:
    permitido: bool
    motivo: str


def avaliar_ferramenta(agente: str, nome: str, ja_executadas: int) -> DecisaoFerramenta:
    if ja_executadas >= LIMITE_FERRAMENTAS:
        return DecisaoFerramenta(False, "teto de ferramentas atingido")
    if nome in FERRAMENTAS_PROIBIDAS:
        return DecisaoFerramenta(False, "ferramenta proibida")
    permitidas = FERRAMENTAS_LEITURA.get(agente, frozenset())
    if nome not in permitidas:
        return DecisaoFerramenta(False, "ferramenta fora da lista do agente")
    return DecisaoFerramenta(True, "leitura permitida")


def passo_dentro_do_limite(iteracao: int) -> bool:
    return iteracao <= LIMITE_PASSOS

"""Defesa em camadas para conteúdo externo e pedidos do usuário.

A normalização e os padrões daqui são independentes do interpretador do modelo
simulado. Os dois não compartilham função de detecção.
"""

from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import dataclass, field

from orquestrador.constantes import SENTINELA_PROMPT

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u180e\u200e\u200f"), None)

# Mapa próprio dos homóglifos cirílicos mais usados em injeção.
_HOMOGLIFOS = str.maketrans(
    {
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "х": "x",
        "у": "y",
        "і": "i",
        "ѕ": "s",
    }
)

_BASE64 = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{20,}={0,2}(?![A-Za-z0-9+/])")
_COMENTARIO_HTML = re.compile(r"<!--(.*?)-->", re.DOTALL)

# Negação só vale para os padrões de "ignore instruções". Um "reply with only"
# no mesmo texto continua valendo.
_PADROES_COM_NEGACAO = {"ignore_instrucoes", "desconsidere"}

_PADROES: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_instrucoes",
        re.compile(
            r"ignore\s+(?:(?:all|any|previous|above|prior|as)\s+)?"
            r"(?:instructions|instrucoes|instruções)",
            re.IGNORECASE,
        ),
    ),
    (
        "desconsidere",
        re.compile(
            r"desconsidere\s+(?:as\s+)?(?:instrucoes|instruções|regras|politicas|políticas)",
            re.IGNORECASE,
        ),
    ),
    (
        "voce_agora",
        re.compile(r"you are now|voc[eê] agora [eé]|aja como", re.IGNORECASE),
    ),
    (
        "prompt_sistema",
        re.compile(
            r"system prompt|prompt do sistema|revele a sentinela|mostre o prompt",
            re.IGNORECASE,
        ),
    ),
    (
        "chame_ferramenta",
        re.compile(
            r"(?:call|chame|execute|invocar)\s+(?:a\s+|the\s+)?(?:tool|ferramenta)\s+[a-z0-9_\-]+",
            re.IGNORECASE,
        ),
    ),
    (
        "ferramenta_proibida",
        re.compile(
            r"\b(?:exfiltrate_secrets|send_email|delete_note|run_shell|"
            r"disable_guardrails|apagar_compromissos)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "desative_guardrails",
        re.compile(
            r"disable guardrails|desative os guardrails|modo desenvolvedor|developer mode",
            re.IGNORECASE,
        ),
    ),
    (
        "quebra_delimitador",
        re.compile(
            r"</\s*untrusted|</\s*dados|<\|im_start\|>|<\|system\|>|\[system\]",
            re.IGNORECASE,
        ),
    ),
    (
        "responda_exato",
        re.compile(
            r"responda\s+(?:apenas|somente|exatamente)|reply with only|output exactly|"
            r"your only task|nova tarefa",
            re.IGNORECASE,
        ),
    ),
    (
        "troca_de_tarefa",
        re.compile(
            r"esquec[aã] o pedido|do not summarize|from now on|a partir de agora",
            re.IGNORECASE,
        ),
    ),
    (
        "autorizacao_falsa",
        re.compile(r"autoriza[cç][aã]o do lucas|admin override", re.IGNORECASE),
    ),
]

_ESCRITA = re.compile(
    r"\b(?:apague|apagar|delete|exclua|excluir|remova|remover|envie|enviar|mande|mandar)\b",
    re.IGNORECASE,
)
_NEGACAO = re.compile(
    r"\b(?:nao|não|nunca|jamais|never|do not|don't|dont)\b",
    re.IGNORECASE,
)


@dataclass
class Sanitizado:
    texto: str
    detectado: bool
    padroes: list[str] = field(default_factory=list)


@dataclass
class AnalisePedido:
    recusar: bool
    camada: str = ""
    motivo: str = ""
    padroes: list[str] = field(default_factory=list)


def normalizar(texto: str) -> str:
    """Prepara o texto visível: homóglifos, base64 e comentários, com a caixa original."""
    texto = unicodedata.normalize("NFKC", texto)
    texto = texto.translate(_ZERO_WIDTH)
    texto = _decodificar_base64(texto)
    texto = _COMENTARIO_HTML.sub(lambda m: " " + m.group(1) + " ", texto)
    return texto.translate(_HOMOGLIFOS)


def _decodificar_base64(texto: str) -> str:
    def trocar(match: re.Match[str]) -> str:
        token = match.group(0)
        try:
            bruto = base64.b64decode(token, validate=True)
        except Exception:
            return token
        if not bruto or any(b not in range(9, 14) and b not in range(32, 127) for b in bruto):
            return token
        decodificado = bruto.decode("ascii", errors="ignore")
        letras = sum(caractere.isalpha() for caractere in decodificado)
        if letras < 8:
            return token
        return decodificado

    return _BASE64.sub(trocar, texto)


def _negado(texto: str, inicio: int) -> bool:
    janela = texto[max(0, inicio - 24) : inicio]
    return _NEGACAO.search(janela) is not None


def detectar(texto: str) -> list[str]:
    base = texto.lower()
    achados: list[str] = []
    for nome, padrao in _PADROES:
        for match in padrao.finditer(base):
            if nome in _PADROES_COM_NEGACAO and _negado(base, match.start()):
                continue
            achados.append(nome)
            break
    return achados


def sanitizar_conteudo_externo(texto: str, origem: str) -> Sanitizado:
    normal = normalizar(texto)
    partes = re.split(r"\n+", normal)
    limpas: list[str] = []
    padroes: list[str] = []
    for parte in partes:
        if not parte.strip():
            continue
        achados = detectar(parte)
        if achados:
            padroes.extend(achados)
            limpas.append("[CONTEUDO_BLOQUEADO: injecao_suspeita]")
        else:
            limpas.append(parte.replace("<", "‹").replace(">", "›"))
    corpo = "\n".join(limpas)
    embrulho = (
        f"‹dados_nao_confiaveis origem=\"{origem}\"›\n{corpo}\n‹/dados_nao_confiaveis›"
    )
    vistos: list[str] = []
    for nome in padroes:
        if nome not in vistos:
            vistos.append(nome)
    return Sanitizado(texto=embrulho, detectado=bool(vistos), padroes=vistos)


def analisar_pedido_usuario(pergunta: str) -> AnalisePedido:
    normal = normalizar(pergunta)
    if _ESCRITA.search(normal):
        return AnalisePedido(
            recusar=True,
            camada="politica_autonomia",
            motivo="pedido de escrita, envio ou exclusao",
        )
    achados = detectar(normal)
    if achados:
        return AnalisePedido(
            recusar=True,
            camada="deteccao",
            motivo="pedido com cara de injecao",
            padroes=achados,
        )
    return AnalisePedido(recusar=False)


def filtrar_saida(texto: str) -> tuple[str, bool]:
    novo = texto.replace(SENTINELA_PROMPT, "[REMOVIDO]")
    novo = re.sub(r"sk-[A-Za-z0-9]{8,}", "[REMOVIDO]", novo)
    novo = re.sub(r"AKIA[A-Z0-9]{16}", "[REMOVIDO]", novo)
    return novo, novo != texto

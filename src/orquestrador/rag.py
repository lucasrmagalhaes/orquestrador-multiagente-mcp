"""Retriever local por TF-IDF. Sem download de modelo e sem chave."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

STOPWORDS = frozenset(
    {
        "das",
        "dos",
        "uma",
        "uns",
        "umas",
        "para",
        "por",
        "com",
        "sem",
        "que",
        "como",
        "sobre",
        "quando",
        "onde",
        "qual",
        "quais",
        "este",
        "esta",
        "isso",
        "the",
        "and",
        "tenho",
        "dizem",
        "fale",
        "falar",
        "notas",
    }
)


@dataclass
class Trecho:
    fonte: str
    texto: str
    vetor: dict[str, float]


def tokenizar(texto: str) -> list[str]:
    normal = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in normal if not unicodedata.combining(c))
    return [
        token
        for token in re.findall(r"[a-z0-9]{3,}", sem_acento.lower())
        if token not in STOPWORDS
    ]


def _fatiar(texto: str, fonte: str) -> list[tuple[str, str]]:
    partes = [parte.strip() for parte in re.split(r"\n\s*\n", texto) if parte.strip()]
    if not partes:
        return [(fonte, texto.strip())]
    titulo = partes[0]
    return [(fonte, parte if parte == titulo else f"{titulo}\n{parte}") for parte in partes]


def _vetor(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    frequencia = Counter(tokens)
    return {
        token: (1 + math.log(contagem)) * idf.get(token, 0.0)
        for token, contagem in frequencia.items()
    }


def _cosseno(esquerda: dict[str, float], direita: dict[str, float]) -> float:
    if not esquerda or not direita:
        return 0.0
    comum = set(esquerda) & set(direita)
    produto = sum(esquerda[token] * direita[token] for token in comum)
    norma_e = math.sqrt(sum(valor * valor for valor in esquerda.values()))
    norma_d = math.sqrt(sum(valor * valor for valor in direita.values()))
    if norma_e == 0 or norma_d == 0:
        return 0.0
    return produto / (norma_e * norma_d)


class IndiceNotas:
    def __init__(self, trechos: list[Trecho]) -> None:
        self.trechos = trechos

    @classmethod
    def carregar(cls, pasta: Path) -> "IndiceNotas":
        brutos: list[tuple[str, str]] = []
        if pasta.exists():
            for arquivo in sorted(pasta.glob("*.md")):
                brutos.extend(_fatiar(arquivo.read_text(encoding="utf-8"), arquivo.name))
        documentos = [(fonte, texto, tokenizar(texto)) for fonte, texto in brutos]
        df: Counter[str] = Counter()
        for _, _, tokens in documentos:
            df.update(set(tokens))
        total = max(len(documentos), 1)
        idf = {token: math.log((1 + total) / (1 + freq)) + 1 for token, freq in df.items()}
        trechos = [
            Trecho(fonte, texto, _vetor(tokens, idf)) for fonte, texto, tokens in documentos
        ]
        indice = cls(trechos)
        indice._idf = idf
        return indice

    def buscar(self, consulta: str, k: int = 3) -> list[Trecho]:
        if not self.trechos:
            return []
        consulta_vetor = _vetor(tokenizar(consulta), self._idf)
        ordenados = sorted(
            self.trechos,
            key=lambda trecho: _cosseno(consulta_vetor, trecho.vetor),
            reverse=True,
        )
        return [trecho for trecho in ordenados if _cosseno(consulta_vetor, trecho.vetor) > 0][:k]

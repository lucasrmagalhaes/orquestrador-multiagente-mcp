"""Funções de leitura usadas pelos servidores MCP e pelo modo em processo."""

from __future__ import annotations

import json

from orquestrador.caminhos import diretorio_dados
from orquestrador.rag import IndiceNotas


def _ler_json(nome: str) -> list[dict]:
    caminho = diretorio_dados() / nome
    if not caminho.exists():
        return []
    return json.loads(caminho.read_text(encoding="utf-8"))


def listar_compromissos(dia: str) -> str:
    """Lista compromissos de exemplo de um dia no formato YYYY-MM-DD."""
    itens = [item for item in _ler_json("agenda.json") if item.get("dia") == dia]
    if not itens:
        return "Nenhum compromisso neste dia."
    return "\n".join(
        f"{item['hora']} {item['titulo']} ({item['local']})" for item in itens
    )


def buscar_compromisso(termo: str) -> str:
    """Busca compromissos de exemplo pelo título ou pelo local."""
    from orquestrador.rag import tokenizar

    termos = set(tokenizar(termo))
    linhas = []
    for item in _ler_json("agenda.json"):
        texto = f"{item['titulo']} {item['local']} {item['dia']}"
        if termos & set(tokenizar(texto)):
            linhas.append(f"{item['dia']} {item['hora']} {item['titulo']} ({item['local']})")
    return "\n".join(linhas) if linhas else "Nenhum compromisso encontrado."


def listar_notas() -> str:
    """Lista os arquivos de notas de exemplo."""
    pasta = diretorio_dados() / "notas"
    if not pasta.exists():
        return "Nenhuma nota de exemplo."
    nomes = sorted(arquivo.name for arquivo in pasta.glob("*.md"))
    return "\n".join(nomes) if nomes else "Nenhuma nota de exemplo."


def buscar_notas(consulta: str) -> str:
    """Recupera trechos de notas de exemplo por TF-IDF."""
    indice = IndiceNotas.carregar(diretorio_dados() / "notas")
    trechos = indice.buscar(consulta, k=3)
    if not trechos:
        return "Nenhum trecho relevante nas notas de exemplo."
    blocos = [f"Fonte: {trecho.fonte}\n{trecho.texto}" for trecho in trechos]
    return "\n\n".join(blocos)


def listar_issues(consulta: str) -> str:
    """Lista issues de exemplo do GitHub e do Jira, filtradas por palavras."""
    from orquestrador.rag import tokenizar

    termos = set(tokenizar(consulta))
    consulta_baixa = consulta.lower()
    so_abertas = "aberta" in consulta_baixa or "abertas" in consulta_baixa
    pontuados = []
    for issue in _ler_json("issues.json"):
        if so_abertas and issue.get("estado") != "aberta":
            continue
        texto = f"{issue['titulo']} {issue['corpo']} {issue['fonte']} {issue['id']}"
        score = len(termos & set(tokenizar(texto)))
        pontuados.append((score, issue))
    pontuados.sort(key=lambda par: par[0], reverse=True)
    escolhidas = [issue for score, issue in pontuados if score > 0][:3]
    if not escolhidas:
        escolhidas = [issue for _, issue in pontuados[:2]]
    if not escolhidas:
        return "Nenhuma issue de exemplo."
    linhas = []
    for issue in escolhidas:
        linhas.append(
            f"{issue['fonte']} {issue['id']} [{issue['estado']}] {issue['titulo']}\n{issue['corpo']}"
        )
    return "\n\n".join(linhas)


def ler_issue(identificador: str) -> str:
    """Lê uma issue de exemplo pelo id, por exemplo GH-101 ou AI-22."""
    for issue in _ler_json("issues.json"):
        if issue.get("id", "").lower() == identificador.lower():
            return (
                f"{issue['fonte']} {issue['id']} [{issue['estado']}] {issue['titulo']}\n"
                f"{issue['corpo']}"
            )
    return "Issue de exemplo não encontrada."


FERRAMENTAS = {
    "listar_compromissos": listar_compromissos,
    "buscar_compromisso": buscar_compromisso,
    "listar_notas": listar_notas,
    "buscar_notas": buscar_notas,
    "listar_issues": listar_issues,
    "ler_issue": ler_issue,
}

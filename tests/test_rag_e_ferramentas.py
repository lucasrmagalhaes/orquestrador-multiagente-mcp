from orquestrador.caminhos import diretorio_dados
from orquestrador.ferramentas import buscar_notas, listar_compromissos, listar_issues
from orquestrador.rag import IndiceNotas


def test_rag_encontra_a_nota_de_guardrails():
    indice = IndiceNotas.carregar(diretorio_dados() / "notas")
    trechos = indice.buscar("guardrails e autonomia", k=1)
    assert trechos
    assert trechos[0].fonte == "guardrails.md"


def test_rag_encontra_checkpoint():
    indice = IndiceNotas.carregar(diretorio_dados() / "notas")
    trechos = indice.buscar("checkpoint de retomada", k=1)
    assert trechos[0].fonte == "llmops.md"


def test_agenda_do_dia():
    texto = listar_compromissos("2026-11-21")
    assert "Daily do time de plataforma" in texto
    assert "Entrevista de sistema" in texto


def test_issues_abertas_do_retriever():
    texto = listar_issues("Quais issues estão abertas sobre o retriever?")
    assert "GH-101" in texto
    assert "GH-88" not in texto

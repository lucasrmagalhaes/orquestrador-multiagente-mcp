from pathlib import Path

from orquestrador.redteam import executar_suite, frase_taxa, tabela_markdown


def test_readme_repete_a_suite_real():
    relatorio = executar_suite()
    readme = Path("README.md").read_text(encoding="utf-8")
    assert frase_taxa(relatorio) in readme
    assert "Pedidos benignos de controle: 4 de 4." in readme
    inicio = readme.split("<!-- tabela:inicio -->", 1)[1]
    tabela = inicio.split("<!-- tabela:fim -->", 1)[0].strip()
    assert tabela == tabela_markdown(relatorio)
    assert "provedor mock" in readme

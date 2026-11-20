from langgraph.checkpoint.sqlite import SqliteSaver

from orquestrador.demo_retomada import demonstrar
from orquestrador.grafo import compilar, executar
from orquestrador.nos import FalhaControlada


def test_retomada_a_partir_do_sqlite(tmp_path, monkeypatch):
    monkeypatch.setenv("ORQUESTRADOR_FALHA_NO", "notas")
    banco = tmp_path / "ckpt.sqlite"
    thread_id = "teste-retomada"
    pergunta = (
        "Quais compromissos tenho em 2026-11-21 e o que as notas dizem sobre guardrails?"
    )
    config = {"configurable": {"thread_id": thread_id}}
    with SqliteSaver.from_conn_string(str(banco)) as saver:
        with pytest_raises(FalhaControlada):
            executar(pergunta, thread_id=thread_id, checkpointer=saver)
        estado = compilar(saver).get_state(config)
        assert estado.next == ("notas",)
        assert any(item["agente"] == "agenda" for item in estado.values["resultados"])
        assert "Daily do time de plataforma" in estado.values["resultados"][0]["texto"]

    monkeypatch.setenv("ORQUESTRADOR_FALHA_NO", "")
    with SqliteSaver.from_conn_string(str(banco)) as saver:
        final = executar(None, thread_id=thread_id, checkpointer=saver, retomar=True)
    assert final.agentes == ["agenda", "notas"]
    assert "Daily do time de plataforma" in final.resposta
    assert "é dado" in final.resposta


def test_script_de_demonstracao(tmp_path, monkeypatch):
    relatorio = demonstrar(tmp_path / "demo.sqlite")
    assert relatorio["proximo_no_momento_da_falha"] == ["notas"]
    assert "Daily do time de plataforma" in relatorio["resposta"]
    assert "é dado" in relatorio["resposta"]


def pytest_raises(erro):
    import pytest

    return pytest.raises(erro)

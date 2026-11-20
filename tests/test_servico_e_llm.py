import json
import threading
import urllib.request

from orquestrador.llm import ChaveAusente, completar
from orquestrador.servico import Servidor


def test_http_health_e_pergunta():
    servidor = Servidor(("127.0.0.1", 0))
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    porta = servidor.server_address[1]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/health") as resposta:
            corpo = json.loads(resposta.read().decode("utf-8"))
        assert corpo["status"] == "ok"
        assert corpo["provedor"] == "mock"
        dados = json.dumps(
            {"pergunta": "Quais compromissos tenho em 2026-11-21?"}
        ).encode("utf-8")
        pedido = urllib.request.Request(
            f"http://127.0.0.1:{porta}/perguntar",
            data=dados,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(pedido) as resposta:
            corpo = json.loads(resposta.read().decode("utf-8"))
        assert "Daily do time de plataforma" in corpo["resposta"]
        assert corpo["agentes"] == ["agenda"]
    finally:
        servidor.shutdown()


def test_cli_aceita_pergunta_solta(capsys):
    from orquestrador.cli import main

    assert main(["Quais compromissos tenho em 2026-11-21?"]) == 0
    assert "Daily do time de plataforma" in capsys.readouterr().out


def test_openai_sem_chave(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    try:
        completar("sistema", "usuario")
    except ChaveAusente as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("esperava ChaveAusente")


def test_openai_monta_o_pedido(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "teste")
    monkeypatch.setenv("LLM_MODEL", "modelo-teste")
    capturado = {}

    class FalsaResposta:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "{\"agentes\": [\"notas\"]}"}}]}
            ).encode("utf-8")

    def falso_urlopen(pedido, timeout=0):
        capturado["url"] = pedido.full_url
        capturado["corpo"] = json.loads(pedido.data.decode("utf-8"))
        capturado["auth"] = pedido.get_header("Authorization")
        return FalsaResposta()

    monkeypatch.setattr("urllib.request.urlopen", falso_urlopen)
    texto = completar("sistema", "usuario")
    assert "notas" in texto
    assert capturado["url"] == "https://api.openai.com/v1/chat/completions"
    assert capturado["corpo"]["model"] == "modelo-teste"
    assert capturado["auth"] == "Bearer teste"

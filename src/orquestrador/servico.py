"""HTTP mínimo para o contêiner e para Cloud Run ou ECS."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from orquestrador.grafo import executar
from orquestrador.llm import ChaveAusente, ProvedorErro, provedor_atual
from orquestrador.nos import FalhaControlada


def criar_checkpointer():
    caminho = os.environ.get("ORQUESTRADOR_CHECKPOINT", "").strip()
    if not caminho:
        return MemorySaver()
    conexao = sqlite3.connect(caminho, check_same_thread=False)
    return SqliteSaver(conexao)


class Servidor(ThreadingHTTPServer):
    def __init__(self, endereco: tuple[str, int], checkpointer=None) -> None:
        super().__init__(endereco, Tratador)
        self.checkpointer = checkpointer if checkpointer is not None else criar_checkpointer()
        self.trava = threading.Lock()


class Tratador(BaseHTTPRequestHandler):
    server: Servidor

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] == "/health":
            self._json(200, {"status": "ok", "provedor": provedor_atual()})
            return
        self._json(404, {"erro": "caminho nao encontrado"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != "/perguntar":
            self._json(404, {"erro": "caminho nao encontrado"})
            return
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            bruto = self.rfile.read(tamanho).decode("utf-8")
            carga = json.loads(bruto or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            self._json(400, {"erro": "json invalido"})
            return
        thread_id = str(carga.get("thread_id") or uuid.uuid4())
        retomar = bool(carga.get("retomar"))
        pergunta = str(carga.get("pergunta") or "")
        if not retomar and not pergunta.strip():
            self._json(400, {"erro": "pergunta vazia"})
            return
        try:
            with self.server.trava:
                resultado = executar(
                    None if retomar else pergunta,
                    thread_id=thread_id,
                    checkpointer=self.server.checkpointer,
                    retomar=retomar,
                )
        except FalhaControlada as exc:
            self._json(409, {"erro": str(exc), "thread_id": thread_id, "retomavel": True})
            return
        except ChaveAusente as exc:
            self._json(503, {"erro": str(exc)})
            return
        except ProvedorErro as exc:
            self._json(502, {"erro": str(exc)})
            return
        self._json(
            200,
            {
                "resposta": resultado.resposta,
                "agentes": resultado.agentes,
                "recusa": resultado.recusa,
                "thread_id": resultado.thread_id,
                "ferramentas_executadas": resultado.ferramentas_executadas,
                "ferramentas_recusadas": resultado.ferramentas_recusadas,
                "bloqueios": resultado.bloqueios,
                "trace": resultado.trace,
            },
        )

    def log_message(self, formato: str, *args) -> None:
        return

    def _json(self, status: int, carga: dict) -> None:
        corpo = json.dumps(carga, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


def servir(host: str = "0.0.0.0", porta: int | None = None) -> None:
    escolhida = porta if porta is not None else int(os.environ.get("PORT", "8080"))
    httpd = Servidor((host, escolhida))
    httpd.serve_forever()

FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin app

COPY pyproject.toml README.md ./
COPY src ./src
COPY mcp_servers ./mcp_servers

RUN pip install --no-cache-dir . \
    && chown -R app:app /app

USER app

ENV PYTHONUNBUFFERED=1 \
    LLM_PROVIDER=mock \
    ORQUESTRADOR_MCP=stdio \
    ORQUESTRADOR_RAIZ=/app \
    PORT=8080

EXPOSE 8080

CMD ["python", "-m", "orquestrador", "servir"]

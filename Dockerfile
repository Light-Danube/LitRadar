# LitBeacon local-first browser workspace (legacy repository name: LitRadar)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Start with core + web dependencies; Textual and LLM providers remain optional.
COPY requirements.txt requirements-web.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt -r requirements-web.txt

COPY . /app
RUN mkdir -p /app/data /app/reports /app/logs

EXPOSE 8765

# The CLI intentionally disallows non-loopback binding. Uvicorn binds inside
# Docker while Compose publishes ONLY to 127.0.0.1 on the host.
CMD ["sh", "-c", "python cli.py init && exec python -m uvicorn workspace_web:create_app --factory --host 0.0.0.0 --port 8765"]

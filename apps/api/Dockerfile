# ---------------------------------------------------------------------------
# Stage 1 — instalar dependencias de producao
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

COPY apps/api/requirements-prod.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-prod.txt

# ---------------------------------------------------------------------------
# Stage 2 — imagem final enxuta
# ---------------------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Copiar pacotes instalados no stage anterior
COPY --from=builder /install /usr/local

# Copiar codigo fonte necessario para a API
COPY src/ src/
COPY desktop/ desktop/
COPY apps/__init__.py apps/__init__.py
COPY apps/api/ apps/api/

# Variavel de ambiente padrao (substituida pela Railway via PORT)
ENV PORT=8000

CMD ["sh", "-c", "uvicorn apps.api.app.main:app --host 0.0.0.0 --port ${PORT}"]

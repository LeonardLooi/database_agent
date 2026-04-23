# Builder stage — installs system build deps and Python packages into a venv
FROM python:3.14-slim AS builder
WORKDIR /app

# Enterprise: accept corporate CA and proxy settings as build args.
# ARGs reset after each FROM — must be redeclared in every stage.
# Usage: docker build --build-arg CORPORATE_CA_CERT="$(cat corp.crt)" ...
# Or set in .env and wired through docker-compose build args (see docker-compose.yml).
ARG CORPORATE_CA_CERT=""
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Install corporate CA BEFORE any HTTPS operations (apt repos, curl, pip).
# Skipped when CORPORATE_CA_CERT is empty (non-enterprise builds).
RUN if [ -n "${CORPORATE_CA_CERT}" ]; then \
    echo "${CORPORATE_CA_CERT}" > /usr/local/share/ca-certificates/corporate-ca.crt && \
    update-ca-certificates; \
fi

RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg2 \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
# Point pip at the system CA bundle — picks up corporate CA when installed above.
# pip defaults to certifi's bundled certs which exclude corporate CAs.
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt

COPY requirements.txt .
# BuildKit cache mount avoids re-downloading packages on every rebuild
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Runtime stage — only runtime system deps, no build headers or key-import tools
FROM python:3.14-slim AS runtime
WORKDIR /app

# ARGs reset after FROM — redeclare in every stage
ARG CORPORATE_CA_CERT=""
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Corporate CA must be installed before curl downloads the Microsoft signing key
RUN if [ -n "${CORPORATE_CA_CERT}" ]; then \
    echo "${CORPORATE_CA_CERT}" > /usr/local/share/ca-certificates/corporate-ca.crt && \
    update-ca-certificates; \
fi

RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg2 \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc curl gosu \
    && apt-get purge -y --auto-remove gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Explicit UID/GID 1001 — avoids collision with host UIDs and matches skill standard
RUN groupadd -g 1001 appgroup && useradd -r -u 1001 -g appgroup appuser

# COPY --chown avoids a separate chown layer — cheaper than chown -R in RUN
COPY --from=builder --chown=appuser:appgroup /venv /venv
ENV PATH="/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY --chown=appuser:appgroup . .

RUN mkdir -p /app/data /app/config/intents /app/config/prompts \
    && chown appuser:appgroup /app/data /app/config/intents /app/config/prompts

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# Entrypoint handles: chown /app/data → SQLite backup → prune old backups → alembic → exec appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

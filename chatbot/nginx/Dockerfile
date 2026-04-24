FROM nginx:1.27-alpine

# Enterprise: accept corporate CA as build arg.
ARG CORPORATE_CA_CERT=""

RUN if [ -n "${CORPORATE_CA_CERT}" ]; then \
    echo "${CORPORATE_CA_CERT}" > /usr/local/share/ca-certificates/corporate-ca.crt && \
    update-ca-certificates; \
fi

# Generate self-signed TLS certificate for HTTPS.
# For production, mount a real certificate via volume or replace these files.
RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/server.key \
        -out /etc/nginx/ssl/server.crt \
        -subj "/C=US/ST=Local/L=Local/O=ChatbotDev/CN=localhost" && \
    chmod 600 /etc/nginx/ssl/server.key

COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- --no-check-certificate https://localhost/health || exit 1

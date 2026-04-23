FROM nginx:1.27-alpine

# Enterprise: accept corporate CA as build arg.
# nginx build only copies config — no package downloads needed.
# CA is injected here for consistency and in case nginx plugins are added later.
ARG CORPORATE_CA_CERT=""

RUN if [ -n "${CORPORATE_CA_CERT}" ]; then \
    echo "${CORPORATE_CA_CERT}" > /usr/local/share/ca-certificates/corporate-ca.crt && \
    update-ca-certificates; \
fi

COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

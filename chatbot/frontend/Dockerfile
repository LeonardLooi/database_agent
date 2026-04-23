FROM node:24-alpine AS builder
WORKDIR /app

# Enterprise: accept corporate CA and proxy settings as build args.
# ARGs reset after each FROM — must be redeclared in every stage.
ARG CORPORATE_CA_CERT=""
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Install corporate CA before npm install — Alpine uses update-ca-certificates
RUN if [ -n "${CORPORATE_CA_CERT}" ]; then \
    echo "${CORPORATE_CA_CERT}" > /usr/local/share/ca-certificates/corporate-ca.crt && \
    update-ca-certificates; \
fi

COPY package*.json ./
# Point npm at the system CA bundle — picks up corporate CA when installed above
RUN npm config set cafile /etc/ssl/certs/ca-certificates.crt && npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# ARGs reset after FROM — redeclare in every stage
ARG CORPORATE_CA_CERT=""

RUN if [ -n "${CORPORATE_CA_CERT}" ]; then \
    echo "${CORPORATE_CA_CERT}" > /usr/local/share/ca-certificates/corporate-ca.crt && \
    update-ca-certificates; \
fi

COPY --from=builder /app/dist/chatbot-frontend/browser /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
# nginx official image runs envsubst on /etc/nginx/templates/*.template at startup
# Set BACKEND_URL at deploy time, e.g. https://backend-xxx.run.app
ENV BACKEND_URL=http://backend:8000
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

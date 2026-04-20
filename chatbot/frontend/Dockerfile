FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist/chatbot-frontend/browser /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
# nginx official image runs envsubst on /etc/nginx/templates/*.template at startup
# Set BACKEND_URL at deploy time, e.g. https://backend-xxx.run.app
ENV BACKEND_URL=http://backend:8000
EXPOSE 80

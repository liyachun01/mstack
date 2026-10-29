FROM node:24.21.0-bookworm-slim@sha256:ba6b7d0ee561d9d49deb99e2b93c98632cc287b6cca1a6b18d66127054efa4dc
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --omit=dev --no-audit --no-fund
USER 501:501
ENTRYPOINT ["node"]

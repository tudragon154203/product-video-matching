FROM node:20-bookworm-slim

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
# Use clean, deterministic install
RUN npm ci --no-audit --no-fund

EXPOSE 3000

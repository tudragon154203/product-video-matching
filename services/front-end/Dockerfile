FROM node:20-bookworm-slim

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
# Use clean, deterministic install
RUN npm ci --no-audit --no-fund && npm install @next/swc-linux-x64-gnu --no-save

EXPOSE 3000

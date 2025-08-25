FROM node:22.18.0-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

EXPOSE 3000
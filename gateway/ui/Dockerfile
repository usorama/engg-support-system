# ESS Chat UI - Production Dockerfile
# Multi-stage build for minimal image size

# Stage 1: Build
FROM node:22-alpine AS builder

WORKDIR /app

# Build arguments for environment variables
ARG VITE_ESS_API_KEY=""
ARG VITE_API_BASE_URL=""

# Set environment variables for Vite build
ENV VITE_ESS_API_KEY=$VITE_ESS_API_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source
COPY . .

# Build production bundle (uses VITE_ env vars)
RUN npm run build

# Stage 2: Production
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:80/health || exit 1

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# ============================================================================
# Frontend — Multi-Stage Dockerfile
# ============================================================================
# Stage 1: Install dependencies
# Stage 2: Build the React app (npm run build → /dist)
# Stage 3: Serve with Nginx (tiny final image ~25MB)
# ============================================================================

# Stage 1: Install
FROM node:20-alpine AS installer
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# Stage 2: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=installer /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: Serve
FROM nginx:1.25-alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
# SPA routing: return index.html for all routes
RUN echo 'server { listen 80; location / { root /usr/share/nginx/html; try_files $uri $uri/ /index.html; } }' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

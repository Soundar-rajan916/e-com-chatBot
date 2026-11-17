# Stage 1: Build widget
FROM node:20-alpine AS widget-builder
WORKDIR /widget
COPY widget/package*.json ./
RUN npm ci
COPY widget/ ./
RUN npm run build

# Stage 2: Build storefront frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Copy built widget into frontend public/ so it gets bundled into dist/
COPY --from=widget-builder /widget/dist/widget.js /app/public/widget.js
RUN npm run build

# Stage 3: Production Nginx container
FROM nginx:alpine
COPY --from=frontend-builder /app/dist /usr/share/nginx/html
COPY --from=widget-builder /widget/dist/widget.js /usr/share/nginx/html/widget.js
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]

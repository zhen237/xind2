# M03 BIM+GIS 前端 Dockerfile
# 构建: docker build -t xind2/m03-frontend:latest .
# 运行: docker run -p 80:80 xind2/m03-frontend:latest

# -- Stage 1: Build --
FROM node:22-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --production=false
COPY frontend/ ./
RUN npm run build

# -- Stage 2: Serve --
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

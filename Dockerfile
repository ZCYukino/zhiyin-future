# ===== 阶段 1：构建前端（Vite） =====
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY zcFrontend/package.json zcFrontend/package-lock.json ./
# 国内镜像：避免默认 npm 源超时
RUN npm install --no-audit --no-fund --registry=https://registry.npmmirror.com
COPY zcFrontend/ ./
# 同源部署：前端请求相对路径 /api/v1，由同一容器内的 FastAPI 提供
ENV VITE_API_BASE_URL=/api/v1
RUN npx vite build

# ===== 阶段 2：后端（FastAPI 托管前端产物） =====
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt ./
# 国内镜像：避免默认 PyPI 源连不上（pydantic 等 "from versions: none"）
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY backend/app ./app
COPY backend/seed ./seed
COPY --from=frontend /frontend/dist ./dist

EXPOSE 8000
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]

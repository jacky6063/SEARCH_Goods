# 🎯 Stage 1: 前端文件（無需構建，直接複製）
FROM alpine:latest AS frontend-stage
WORKDIR /frontend
COPY frontend/ .

# 🔧 Stage 2: Python 依賴構建
FROM python:3.10-slim AS builder
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
	&& python -m pip install --upgrade pip setuptools wheel \
	&& pip install --no-cache-dir -r /app/requirements.txt \
	&& pip install --no-cache-dir gunicorn==23.0.0 \
	&& rm -rf /var/lib/apt/lists/*

# 🚀 Stage 3: 最終應用鏡像
FROM python:3.10-slim
WORKDIR /app
# 創建非 root 用戶
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
# 複製 Python 依賴和 gunicorn
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn
# 複製後端代碼
COPY backend/ /app/backend/
# 🎯 複製前端文件到後端靜態目錄
COPY --from=frontend-stage /frontend/ /app/backend/static/
ENV PYTHONUNBUFFERED=1
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
# 🎯 啟動後端應用，提供前端靜態文件
CMD ["gunicorn", "-c", "backend/gunicorn_conf.py", "backend.app:app"]

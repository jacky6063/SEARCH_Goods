FROM python:3.10-slim AS builder
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
COPY requirements_hotfix.txt /app/requirements_hotfix.txt
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
	&& python -m pip install --upgrade pip setuptools wheel \
	&& pip install --no-cache-dir -r /app/requirements.txt \
	&& pip install --no-cache-dir -r /app/requirements_hotfix.txt \
	&& pip install --no-cache-dir gunicorn==23.0.0 \
	&& rm -rf /var/lib/apt/lists/*

FROM python:3.10-slim
WORKDIR /app
# create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY . /app
ENV PYTHONUNBUFFERED=1
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["gunicorn", "-c", "backend/gunicorn_conf.py", "backend.app:app"]

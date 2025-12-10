FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEADLESS=true \
    TZ=Asia/Shanghai \
    STORAGE_DIR=/data/storage

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install-deps \
    && apt-get update \
    && apt-get install -y tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && python -m playwright install chromium

COPY app ./app
RUN mkdir -p /data/storage

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

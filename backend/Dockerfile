FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:///./data/sentiment.db \
    CORS_ORIGINS=http://localhost:3000 \
    ENABLE_SCHEDULER=true

EXPOSE 8000

# Railway injects $PORT; default 8000 for local Docker
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

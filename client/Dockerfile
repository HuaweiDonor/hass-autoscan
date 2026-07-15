FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY config/config.example.yaml ./config/config.example.yaml

VOLUME ["/app/config", "/app/data"]

CMD ["python3", "-m", "app.main"]

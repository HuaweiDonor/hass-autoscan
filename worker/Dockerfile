FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3.11-dev python3-pip \
        ffmpeg libgl1 libglib2.0-0 git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install torch with CUDA 12.1 support first so nomeroff-net picks it up
# instead of pulling a CPU-only wheel.
RUN python3.11 -m pip install --no-cache-dir \
        torch torchvision --index-url https://download.pytorch.org/whl/cu121

COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY config/config.example.yaml ./config/config.example.yaml

VOLUME ["/app/config", "/app/data"]

CMD ["python3.11", "-m", "app.main"]

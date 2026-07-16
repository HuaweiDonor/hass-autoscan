FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    LOCAL_STORAGE=/app/models

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

# nomeroff-net's v4.0.0 release is missing __init__.py in this subpackage
# (an upstream packaging bug: https://github.com/ria-com/nomeroff-net/issues/315
# family of issues). Whether setuptools/pip includes it anyway is
# non-deterministic (depends on git clone completeness at install time),
# so guarantee it exists rather than rely on luck. Note: this deliberately
# does NOT `import nomeroff_net` to find its install path -- doing so runs
# nomeroff_net/__init__.py, which reaches out to models.vsp.net.ua at
# import time (via ModelHub's module-level init in tools/mcm.py), and that
# host isn't reachable from every network this builds on. The install path
# is deterministic for this base image + python3.11 + pip combination.
RUN touch /usr/local/lib/python3.11/dist-packages/nomeroff_net/pipes/number_plate_keypoints_detectors/__init__.py

COPY app/ ./app/
COPY config/config.example.yaml ./config/config.example.yaml

VOLUME ["/app/config", "/app/data", "/app/models"]

CMD ["python3.11", "-m", "app.main"]

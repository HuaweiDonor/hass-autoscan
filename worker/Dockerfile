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

# Vendored instead of `pip install git+https://github.com/ria-com/nomeroff-net...`:
# a live git clone during `pip install` was unreliable on this network,
# non-deterministically dropping files mid-clone (including, in one case,
# an entire missing subpackage, nomeroff_net/pipes/number_plate_keypoints_detectors/
# -- itself also missing an __init__.py upstream, a separate packaging bug
# in v4.0.0: https://github.com/ria-com/nomeroff-net/issues/315 family).
# This is a verified-complete copy (only the code needed to install the
# package, not the upstream repo's tutorials/data/blog directories) with
# that missing __init__.py added.
COPY vendor/nomeroff-net /app/vendor/nomeroff-net

COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY config/config.example.yaml ./config/config.example.yaml

VOLUME ["/app/config", "/app/data", "/app/models"]

CMD ["python3.11", "-m", "app.main"]

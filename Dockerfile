FROM python:3.11-slim

ARG CACHEBUST=20260606T0430Z-v2.9-cpu-torch

WORKDIR /app

# v2.6 — Mesa + symlink fallback for libGLESv2 (force apt rebuild)
RUN echo "Build: $CACHEBUST" \
    && apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgles2 \
    libegl1 \
    libegl-mesa0 \
    libgl1-mesa-dri \
    libglx-mesa0 \
    curl \
    && ldconfig \
    && echo "Available GLES libs:" \
    && find / -name "libGLESv2*" 2>/dev/null || echo "  none found" \
    && rm -rf /var/lib/apt/lists/*

COPY cv_backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# cache bust — esta línea invalida la capa de código con cada CACHEBUST
RUN echo "App copy bust: $CACHEBUST"
COPY cv_backend/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

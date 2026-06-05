FROM python:3.11-slim

WORKDIR /app

# v2.5 — Mesa software OpenGL stack for MediaPipe headless
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && rm -rf /var/lib/apt/lists/*

COPY cv_backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# v2.4 — force cache bust
COPY cv_backend/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

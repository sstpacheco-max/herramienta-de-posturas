FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema para OpenCV y MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY cv_backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cv_backend/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

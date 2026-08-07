FROM python:3.10-slim

# Install system dependencies for dlib and OpenCV
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libx11-6 \
    libxext6 \
    libsm6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run Gunicorn (Railway provides the PORT environment variable)
CMD sh -c "gunicorn -w 1 -b 0.0.0.0:${PORT:-8080} attendance_tracking_app:app"

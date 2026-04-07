# STAGE 1: Builder
FROM python:3.12-slim AS builder

# Install uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Optimizations for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=never

# REQUIRED: Git and Build-essential to install CLIP from GitHub
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies based on your TOML
# This will fetch CLIP from GitHub and build it using setuptools
RUN uv sync --frozen --no-install-project --no-dev


# STAGE 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for OpenCV/Pillow
# (FFmpeg removed as requested)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Model Weight Caching
# CLIP and Sentence-Transformers will use this to avoid redownloading
ENV TORCH_HOME=/app/model_cache
ENV HF_HOME=/app/model_cache

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY app/ ./app/
COPY .env ./

# Ensure storage and cache directories exist
RUN mkdir -p /app/static/videos \
             /app/static/frames \
             /app/model_cache \
             /app/temp_video_uploads

# FastAPI Port
EXPOSE 8000

# Start Application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
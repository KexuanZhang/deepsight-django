# Stage 1: Build Python and install dependencies
# This stage compiles Python and installs all dependencies, including build-time tools,
# into a self-contained virtual environment.
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/opt/venv/bin:$PATH" \
    # NVIDIA environment variables for build stage
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install build-time dependencies required to compile Python and install packages from requirements.txt
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    liblzma-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libsqlite3-dev \
    libreadline-dev \
    libffi-dev \
    libbz2-dev \
    wget \
    curl \
    libpq-dev \
    libmagic-dev \
    pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Compile and install Python 3.12 into a dedicated directory to avoid conflicts
RUN wget --no-check-certificate -O Python-3.12.11.tar.xz https://www.python.org/ftp/python/3.12.11/Python-3.12.11.tar.xz && \
    tar -xf Python-3.12.11.tar.xz && \
    cd Python-3.12.11 && \
    ./configure --enable-optimizations --prefix=/opt/python && \
    make -j$(nproc) && \
    make install && \
    cd / && \
    rm -rf Python-3.12.11*

# Create a virtual environment and install Python packages into it
RUN /opt/python/bin/python3 -m venv /opt/venv
COPY requirements.txt .

# Install packages with proper CUDA environment
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    # Install PyTorch with CUDA support first
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 && \
    # Install other requirements
    pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------------------------------------

# Stage 2: Final production image
# This stage creates the final, lean image by copying only the necessary artifacts
# from the builder stage, resulting in a smaller and more secure image.
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Set the PATH to include the virtual environment's bin directory.
    # This is crucial for commands like 'playwright', 'gunicorn', and 'celery' to be found.
    PATH="/opt/venv/bin:$PATH" \
    DEBIAN_FRONTEND=noninteractive \
    # NVIDIA environment variables for runtime
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    # CUDA environment variables
    CUDA_HOME=/usr/local/cuda \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

WORKDIR /app

# Install ONLY the essential runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libmagic1 \
    postgresql-client \
    netcat-openbsd \
    ffmpeg \
    curl \
    ca-certificates \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    update-ca-certificates

# Copy the Python installation from the builder stage
COPY --from=builder /opt/python /opt/python

# Copy the entire virtual environment from the builder stage.
# This includes all Python packages and their command-line executables.
COPY --from=builder /opt/venv /opt/venv

# Install Playwright browsers and dependencies in the final stage
# This ensures all system dependencies are properly installed
RUN playwright install --with-deps chromium

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy application code last to leverage Docker layer caching.
# The build will be much faster if only the code changes.
COPY . .

# Collect static files if this is a Django project
RUN if [ -f manage.py ]; then /opt/venv/bin/python manage.py collectstatic --noinput; fi

EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# The CMD now uses the entrypoint to handle different service types
CMD ["gunicorn"]
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH" \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies in a single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        curl \
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
        gcc \
        libpq-dev \
        libmagic1 \
        libmagic-dev \
        postgresql-client \
        netcat-openbsd \
        ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python 3.12 from source with optimized build
RUN wget --no-check-certificate -O Python-3.12.11.tar.xz \
    https://www.python.org/ftp/python/3.12.11/Python-3.12.11.tar.xz && \
    tar -xf Python-3.12.11.tar.xz && \
    cd Python-3.12.11 && \
    ./configure --enable-optimizations && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf Python-3.12.11* && \
    ln -sf /usr/local/bin/python3 /usr/local/bin/python && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3 && \
    python -m pip install --upgrade pip

# Install Python dependencies
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps

# Copy application code
COPY . ./

# Collect static files (if Django project)
RUN if [ -f manage.py ]; then python manage.py collectstatic --noinput; fi

EXPOSE 8000
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
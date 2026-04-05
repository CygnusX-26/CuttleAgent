FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /

RUN apt-get update && apt-get install -y --no-install-recommends \
    aapt \
    apktool \
    binutils \
    ca-certificates \
    default-jre-headless \
    file \
    p7zip-full \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv \
    && uv pip install --system .

RUN mkdir -p /apps

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /work

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

COPY pyproject.toml uv.lock ./
COPY src ./src

RUN pip install --no-cache-dir uv \
    && uv pip install --system .

RUN mkdir -p /work/apps /work/findings

# CMD ["python", "-m", "src.main", "--input-dir", "/work/apps", "--output-dir", "/work/findings"]

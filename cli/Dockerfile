FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc g++ gfortran csh nodejs npm chromium \
        fonts-liberation fonts-noto-color-emoji \
    && npm install -g highcharts-export-server@5.1.0 molstar@5.6.1 \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-wrapper

RUN mv /usr/bin/chromium /usr/bin/chromium.real && \
    printf '#!/bin/sh\nexec /usr/bin/chromium.real --no-sandbox --disable-dev-shm-usage "$@"\n' \
        > /usr/bin/chromium-wrapper && \
    chmod +x /usr/bin/chromium-wrapper

COPY . /app/cli
RUN PIP_DEFAULT_TIMEOUT=180 pip install --no-cache-dir --retries 5 /app/cli && \
    chmod +x /app/cli/_runtime/deps/reduce/reduce \
             /app/cli/_runtime/deps/hbplus/hbplus \
             /app/cli/_runtime/deps/hbadd/hbadd \
             /app/cli/_runtime/deps/naccess/naccess \
             /app/cli/_runtime/deps/naccess/accall

ENV COCOMAPS_DEPS_DIR=/app/cli/_runtime/deps
ENV PYTHONUNBUFFERED=1

VOLUME ["/data"]
WORKDIR /data
ENTRYPOINT ["coco-md"]

FROM python:3.11-slim

WORKDIR /app

# Install ONLY the shared libs needed by Chromium (not Chromium itself - Playwright manages that)
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 \
    libcups2t64 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2t64 \
    libatspi2.0-0t64 libwayland-client0 libwayland-cursor0 \
    libwayland-egl1 libxshmfence1 libglib2.0-0t64 \
    && rm -rf /var/lib/apt/lists/*

# Copy package
COPY theoldllm/ /app/theoldllm/
COPY setup.py /app/
COPY README.md /app/
COPY railway/server.py /app/server.py

# Install deps
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir aiohttp playwright

# Install Chromium via Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-browsers
RUN python -m playwright install chromium

# Session storage
RUN mkdir -p /app/data

ENV HOST=0.0.0.0
ENV PORT=8080
ENV STORAGE_PATH=/app/data/session.json

EXPOSE 8080

CMD ["python", "/app/server.py"]

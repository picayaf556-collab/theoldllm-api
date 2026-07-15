FROM python:3.11-slim

WORKDIR /app

# Install Chromium and dependencies for Playwright
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy the theoldllm package
COPY theoldllm/ /app/theoldllm/
COPY setup.py /app/
COPY README.md /app/

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir aiohttp playwright

# Set Playwright browsers path and install Chromium via Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-browsers
RUN python -m playwright install chromium

# Session storage directory
RUN mkdir -p /app/data

COPY railway/server.py /app/server.py

ENV HOST=0.0.0.0
ENV PORT=8080
ENV STORAGE_PATH=/app/data/session.json

EXPOSE 8080

CMD ["python", "/app/server.py"]

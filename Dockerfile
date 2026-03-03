# ─────────────────────────────────────────────────────────────
# Dockerfile — Telegram Forward Bot
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system deps (needed for tgcrypto)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the code
COPY . .

# Expose Flask keep-alive port
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]

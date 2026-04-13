FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install OS dependencies (bash needed for entrypoint)
RUN apt-get update && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts

# Make entrypoint executable
RUN chmod +x scripts/entrypoint.sh

# Media folder for Telegram photo cache (bind-mounted in production)
RUN mkdir -p /app/media

EXPOSE 8000

ENTRYPOINT ["bash", "scripts/entrypoint.sh"]

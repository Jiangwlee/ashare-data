FROM python:3.12-slim

WORKDIR /app
ENV ASHARE_PLATFORM_HOME=/app/runtime

RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g; s|http://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
COPY ashare_data /app/ashare_data
COPY app/app /app/app
COPY app/alembic.ini /app/alembic.ini
COPY app/alembic /app/alembic
COPY app/deploy /app/deploy

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && mkdir -p /var/log/supervisor \
    && apt-get update && apt-get install -y --no-install-recommends cron && rm -rf /var/lib/apt/lists/* \
    && chmod +x /app/deploy/start.sh /app/deploy/run_scheduled_collect.sh \
    && cp /app/deploy/ashare-platform.cron /etc/cron.d/ashare-platform \
    && chmod 644 /etc/cron.d/ashare-platform

EXPOSE 8000

CMD ["bash", "/app/deploy/start.sh"]

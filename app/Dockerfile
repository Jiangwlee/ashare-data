FROM python:3.12-slim

WORKDIR /app
ENV ASHARE_PLATFORM_HOME=/app/runtime

RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g; s|http://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
COPY ashare_data /app/ashare_data
COPY app /app/app

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && mkdir -p /var/log/supervisor

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

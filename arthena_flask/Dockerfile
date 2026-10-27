FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/docker/entrypoint.sh \
    && useradd --create-home --uid 10001 arthena \
    && chown -R arthena:arthena /app

USER arthena

EXPOSE 5000

ENTRYPOINT ["/app/docker/entrypoint.sh"]

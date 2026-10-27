FROM python:3.12-slim-bookworm

# Java para o Spark (modo local) e utilitários de download
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless curl unzip \
 && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PYTHONUNBUFFERED=1 \
    DBT_PROFILES_DIR=/app/dbt

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["bash", "pipeline.sh"]

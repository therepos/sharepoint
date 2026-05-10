FROM python:3.11-slim

# LibreOffice for DOCX → PDF conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Volume mount points (created at deploy time)
VOLUME ["/app/data", "/app/config", "/app/templates"]

EXPOSE 8501

ENV CVGEN_DATA_DIR=/app/data \
    CVGEN_CONFIG_DIR=/app/config \
    CVGEN_TEMPLATES_DIR=/app/templates \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app/main.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]

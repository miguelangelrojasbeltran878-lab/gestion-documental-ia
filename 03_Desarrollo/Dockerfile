FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# Tesseract (OCR local gratuito) con idioma español
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY seed_data.py run.py ./
ENV APP_ENV=production COOKIE_SECURE=true
EXPOSE 8000
# Un solo worker: el scheduler (APScheduler) vive dentro del proceso.
CMD ["sh", "-c", "python seed_data.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

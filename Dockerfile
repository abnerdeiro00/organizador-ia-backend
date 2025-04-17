FROM python:3.10-slim

# Instala OCR + libs necessárias
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# ✅ Usa shell nativa para interpretar $PORT corretamente
ENTRYPOINT ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port=$PORT"]
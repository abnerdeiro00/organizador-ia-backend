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

# Define shell padrão para usar variáveis corretamente
SHELL ["/bin/bash", "-c"]

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos para o container
COPY . .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Inicia o app com a variável de ambiente da Railway
CMD uvicorn main:app --host 0.0.0.0 --port=${PORT}
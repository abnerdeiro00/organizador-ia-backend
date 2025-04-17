# Imagem base oficial do Python
FROM python:3.10-slim

# Instala o Tesseract com idioma português + dependências básicas
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório de trabalho
WORKDIR /app

# Copia os arquivos
COPY . .

# Instala dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando para iniciar o FastAPI com Uvicorn na porta padrão Railway
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

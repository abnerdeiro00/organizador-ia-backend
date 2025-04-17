from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
import os

app = FastAPI()

# Libera CORS para frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={API_KEY}"

PROMPT_PADRAO = (
    "Você é um organizador de arquivos. Analise o conteúdo visual/textual e responda com: "
    "1) Resumo do conteúdo, "
    "2) Nome de arquivo sugerido, "
    "3) Categoria, "
    "4) Caminho de pasta destino sugerido, "
    "5) Tags úteis, "
    "6) Tipo de documento (ex: 1ª edição, 2ª edição, cópia, final), "
    "7) Se parece ser duplicado ou versão de outro arquivo. "
    "Responda em JSON."
)

@app.post("/analisar")
async def analisar_arquivo(file: UploadFile = File(...)):
    conteudo = await file.read()
    base64_data = base64.b64encode(conteudo).decode("utf-8")

    payload = {
        "contents": [{
            "parts": [
                {"text": PROMPT_PADRAO},
                {
                    "inline_data": {
                        "mime_type": file.content_type,
                        "data": base64_data
                    }
                }
            ]
        }]
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(GEMINI_URL, headers=headers, json=payload)
    return response.json()

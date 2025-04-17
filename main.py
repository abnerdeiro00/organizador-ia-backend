from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={API_KEY}"

PROMPT_PADRAO = (
    "Você é um organizador de arquivos inteligente. Dado o conteúdo abaixo, retorne um JSON com:\n"
    "- 'nome_sugerido': nome adequado do arquivo\n"
    "- 'resumo': até 3 frases\n"
    "- 'categoria': ex: Clientes, Projetos, Financeiro...\n"
    "- 'caminho_destino': pasta destino sugerida\n"
    "- 'tags': lista de palavras-chave\n"
    "- 'tipo_documento': ex: 1ª edição, cópia, final\n"
    "- 'duplicado_de': nome de possível original, se for o caso\n"
    "Use português e responda apenas o JSON."
)

def extrair_texto_pdf_com_ocr(pdf_bytes):
    texto_total = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            texto_ocr = pytesseract.image_to_string(img, lang="por")
            texto_total += texto_ocr + "\n\n"
    return texto_total

def extrair_texto_upload(file: UploadFile, file_bytes: bytes) -> str:
    if file.content_type == "application/pdf":
        return extrair_texto_pdf_com_ocr(file_bytes)
    elif file.content_type.startswith("image/"):
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img, lang="por")
    else:
        return file_bytes.decode("utf-8", errors="ignore")

@app.post("/analisar")
async def analisar_arquivo(file: UploadFile = File(...)):
    file_bytes = await file.read()
    conteudo_texto = extrair_texto_upload(file, file_bytes)

    payload = {
        "contents": [{
            "parts": [
                {"text": f"{PROMPT_PADRAO}\n\n---\n\n{conteudo_texto}"}
            ]
        }]
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(GEMINI_URL, headers=headers, json=payload)

    try:
        return response.json()
    except Exception:
        return {"erro": "Resposta inválida da IA", "raw": response.text}
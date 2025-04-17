from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import csv
from datetime import datetime
import json
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Configurações
API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={API_KEY}"

CLIENT_ID = os.getenv("ONEDRIVE_CLIENT_ID")
TENANT_ID = os.getenv("ONEDRIVE_TENANT_ID")
CLIENT_SECRET = os.getenv("ONEDRIVE_CLIENT_SECRET")
SCOPE = "https://graph.microsoft.com/.default"
TOKEN_ENDPOINT = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
CSV_FILENAME = "analises_ia.csv"
ONEDRIVE_FOLDER = "/OrganizadorIA"

# ✅ Prompt atualizado
PROMPT_PADRAO = (
    "Você é um organizador de arquivos inteligente. Dado o conteúdo abaixo, retorne um JSON com:\n"
    "- 'nome_sugerido': nome adequado do arquivo\n"
    "- 'resumo': de 3 a 10 frases conforme necessário\n"
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
        resposta = response.json()

        if "candidates" in resposta:
            content = resposta["candidates"][0]["content"]["parts"][0]["text"]
            dados = json.loads(content)
            dados["data_analise"] = datetime.now().isoformat()
            salvar_csv_local(dados)

            try:
                token = gerar_token_onedrive()
                enviar_para_onedrive(token)
            except Exception as e:
                return {"erro": "Falha ao enviar para OneDrive", "detalhes": str(e), "dados": dados}

            return dados
        else:
            return {"erro": "Resposta inesperada da IA", "resposta_bruta": resposta}
    except Exception as e:
        return {"erro": "Falha geral", "detalhes": str(e)}

@app.post("/varrer")
def iniciar_varredura():
    try:
        resultado = subprocess.run(["python", "varredor_onedrive.py"], capture_output=True, text=True)
        return {
            "status": "executado",
            "stdout": resultado.stdout,
            "stderr": resultado.stderr
        }
    except Exception as e:
        return {"erro": str(e)}

def gerar_token_onedrive():
    data = {
        "client_id": CLIENT_ID,
        "scope": SCOPE,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(TOKEN_ENDPOINT, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def salvar_csv_local(data: dict):
    existe = os.path.exists(CSV_FILENAME)
    with open(CSV_FILENAME, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not existe:
            writer.writeheader()
        writer.writerow(data)

def enviar_para_onedrive(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "text/csv"
    }
    with open(CSV_FILENAME, "rb") as f:
        csv_data = f.read()
    upload_url = f"{GRAPH_ENDPOINT}/me/drive/root:{ONEDRIVE_FOLDER}/{CSV_FILENAME}:/content"
    response = requests.put(upload_url, headers=headers, data=csv_data)
    response.raise_for_status()
    return response.json()
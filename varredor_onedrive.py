import os
import requests
import json
import csv
import io
from datetime import datetime
from PIL import Image
import pytesseract
import fitz  # PyMuPDF

# Variáveis de ambiente necessárias
CLIENT_ID = os.getenv("ONEDRIVE_CLIENT_ID")
TENANT_ID = os.getenv("ONEDRIVE_TENANT_ID")
CLIENT_SECRET = os.getenv("ONEDRIVE_CLIENT_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Constantes
SCOPE = "https://graph.microsoft.com/.default"
TOKEN_ENDPOINT = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_API = "https://graph.microsoft.com/v1.0"
CSV_FILENAME = "analises_ia.csv"
ONEDRIVE_FOLDER = "/OrganizadorIA"
BATCH_LIMIT = 10  # Limite de arquivos por rodada

# Prompt
PROMPT = (
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

def gerar_token():
    data = {
        "client_id": CLIENT_ID,
        "scope": SCOPE,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    r = requests.post(TOKEN_ENDPOINT, data=data)
    r.raise_for_status()
    return r.json()["access_token"]

def listar_arquivos(token, next_url=None):
    headers = {"Authorization": f"Bearer {token}"}
    if not next_url:
        url = f"{GRAPH_API}/me/drive/root/children?$expand=children"
    else:
        url = next_url
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

def baixar_arquivo(token, file_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_API}/me/drive/items/{file_id}/content"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.content

def extrair_texto(nome, content_type, file_bytes):
    if content_type == "application/pdf":
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            texto = ""
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                texto += pytesseract.image_to_string(img, lang="por") + "\n\n"
            return texto
    elif content_type.startswith("image/"):
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img, lang="por")
    else:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except:
            return f"[{nome}] Conteúdo não reconhecido."

def enviar_para_gemini(texto):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"{PROMPT}\n\n---\n\n{texto}"}]
        }]
    }
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()
    resposta = r.json()
    return json.loads(resposta["candidates"][0]["content"]["parts"][0]["text"])

def carregar_csv_existente():
    if not os.path.exists(CSV_FILENAME):
        return []
    with open(CSV_FILENAME, "r", encoding="utf-8") as f:
        return [row["nome_sugerido"] for row in csv.DictReader(f)]

def salvar_csv_local(dados):
    existe = os.path.exists(CSV_FILENAME)
    with open(CSV_FILENAME, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=dados.keys())
        if not existe:
            writer.writeheader()
        writer.writerow(dados)

def enviar_para_onedrive(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/csv"
    }
    with open(CSV_FILENAME, "rb") as f:
        csv_data = f.read()
    upload_url = f"{GRAPH_API}/me/drive/root:{ONEDRIVE_FOLDER}/{CSV_FILENAME}:/content"
    r = requests.put(upload_url, headers=headers, data=csv_data)
    r.raise_for_status()
    return r.json()

def rodar_varredura():
    token = gerar_token()
    analisados = set(carregar_csv_existente())
    arquivos_processados = 0
    next_link = None

    while arquivos_processados < BATCH_LIMIT:
        data = listar_arquivos(token, next_url=next_link)
        arquivos = data.get("value", [])

        for arquivo in arquivos:
            if arquivos_processados >= BATCH_LIMIT:
                break
            if "file" not in arquivo:
                continue
            nome = arquivo["name"]
            tipo = arquivo["file"]["mimeType"]
            if nome in analisados:
                continue

            print(f"🔍 Analisando: {nome}")
            try:
                conteudo = baixar_arquivo(token, arquivo["id"])
                texto = extrair_texto(nome, tipo, conteudo)
                resultado = enviar_para_gemini(texto)
                resultado["nome_sugerido"] = nome
                resultado["data_analise"] = datetime.now().isoformat()
                salvar_csv_local(resultado)
                arquivos_processados += 1
            except Exception as e:
                print(f"Erro ao processar {nome}: {e}")

        next_link = data.get("@odata.nextLink")
        if not next_link:
            break

    enviar_para_onedrive(token)
    print(f"✅ Varredura concluída. {arquivos_processados} arquivos analisados.")

if __name__ == "__main__":
    rodar_varredura()

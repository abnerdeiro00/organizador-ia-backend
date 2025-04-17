import time
print("🚀 Watcher inicializado...")  # ← essa linha nova

from varredor_onedrive import rodar_varredura

if __name__ == "__main__":
    while True:
        print("🔄 Iniciando varredura programada no OneDrive...")
        try:
            rodar_varredura()
        except Exception as e:
            print(f"⛔ Erro durante varredura: {e}")
        print("⏳ Aguardando 1 hora até próxima varredura...")
        time.sleep(3600)
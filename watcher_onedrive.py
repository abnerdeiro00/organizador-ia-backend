import time

print("✅ Container iniciou e watcher está rodando!")

try:
    from varredor_onedrive import rodar_varredura
except Exception as e:
    print(f"⛔ Erro ao importar varredor_onedrive: {e}")
    rodar_varredura = None

if __name__ == "__main__":
    while True:
        if rodar_varredura:
            print("🔄 Iniciando varredura programada no OneDrive...")
            try:
                rodar_varredura()
            except Exception as e:
                print(f"⛔ Erro durante varredura: {e}")
        else:
            print("❌ Função rodar_varredura não disponível. Pulando ciclo...")

        print("⏳ Aguardando 1 hora até próxima varredura...")
        time.sleep(3600)

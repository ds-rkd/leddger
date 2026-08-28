"""
Script de inicialização: cria os cabeçalhos corretos em cada aba da planilha.
Rode uma única vez, após compartilhar a planilha com a Service Account:

    python scripts_init_sheets.py
"""
from config.settings import settings
from services.google_sheets import sheets_service

def main():
    if not sheets_service.is_connected():
        print("❌ Não foi possível conectar ao Google Sheets. Verifique o .env.")
        print("Detalhe:", sheets_service.status()["error"])
        return

    for sheet_name, headers in settings.HEADERS.items():
        try:
            sheets_service.ensure_headers(sheet_name, headers)
            print(f"✔ Cabeçalhos verificados/criados na aba '{sheet_name}'")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ Falha na aba '{sheet_name}': {exc}")
            print(f"   → Confirme que a aba '{sheet_name}' existe na planilha.")

    print("\nConcluído. Abra a planilha para conferir os cabeçalhos.")

if __name__ == "__main__":
    main()

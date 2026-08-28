"""
GoogleSheetsService
--------------------
Camada única responsável por TODA comunicação com o Google Sheets.
Nenhuma outra parte do sistema deve chamar a API do Google diretamente.

Responsabilidades:
- Autenticação via Service Account
- Leitura de abas inteiras
- Inserção de linhas (append)
- Atualização de linhas específicas
- Tratamento de erros e retry com backoff exponencial
"""
import time
import logging
from typing import List, Dict, Any, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import settings

logger = logging.getLogger("google_sheets_service")


class GoogleSheetsError(Exception):
    """Erro de alto nível ao falar com o Google Sheets."""


class GoogleSheetsService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Singleton: evita recriar conexões desnecessariamente
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._service = None
        self._connected = False
        self._last_error = None
        self._initialized = True
        self._connect()

    # ------------------------------------------------------------------ #
    # Conexão
    # ------------------------------------------------------------------ #
    def _connect(self):
        try:
            if not settings.GOOGLE_CREDENTIALS_FILE or not settings.GOOGLE_SHEET_ID:
                raise GoogleSheetsError(
                    "GOOGLE_CREDENTIALS_FILE ou GOOGLE_SHEET_ID não configurados no .env"
                )
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_CREDENTIALS_FILE, scopes=settings.GOOGLE_SCOPES
            )
            self._service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
            self._connected = True
            self._last_error = None
            logger.info("Conectado ao Google Sheets com sucesso.")
        except Exception as exc:  # noqa: BLE001
            self._connected = False
            self._last_error = str(exc)
            logger.error("Falha ao conectar ao Google Sheets: %s", exc)

    def is_connected(self) -> bool:
        return self._connected

    def status(self) -> Dict[str, Any]:
        return {"connected": self._connected, "error": self._last_error}

    # ------------------------------------------------------------------ #
    # Helper interno com retry
    # ------------------------------------------------------------------ #
    def _with_retry(self, func, *args, max_retries: int = 3, **kwargs):
        if not self._connected:
            self._connect()
        if not self._connected:
            raise GoogleSheetsError(self._last_error or "Google Sheets indisponível.")

        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except HttpError as exc:
                last_exc = exc
                status_code = getattr(exc, "status_code", None) or exc.resp.status
                if status_code in (429, 500, 503) and attempt < max_retries:
                    wait = 0.5 * (2 ** (attempt - 1))
                    logger.warning("Sheets API falhou (tentativa %s), retry em %ss", attempt, wait)
                    time.sleep(wait)
                    continue
                raise GoogleSheetsError(f"Erro na API do Google Sheets: {exc}") from exc
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                raise GoogleSheetsError(f"Erro inesperado ao acessar o Google Sheets: {exc}") from exc
        raise GoogleSheetsError(f"Falha após {max_retries} tentativas: {last_exc}")

    # ------------------------------------------------------------------ #
    # Operações de leitura
    # ------------------------------------------------------------------ #
    def read_sheet(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Lê uma aba inteira e retorna uma lista de dicionários (header -> valor)."""

        def _do():
            result = (
                self._service.spreadsheets()
                .values()
                .get(spreadsheetId=settings.GOOGLE_SHEET_ID, range=f"{sheet_name}!A:Z")
                .execute()
            )
            rows = result.get("values", [])
            if not rows:
                return []
            headers = rows[0]
            records = []
            for i, row in enumerate(rows[1:], start=2):
                padded = row + [""] * (len(headers) - len(row))
                record = dict(zip(headers, padded))
                record["_row"] = i  # número da linha real na planilha (para updates)
                records.append(record)
            return records

        return self._with_retry(_do)

    # ------------------------------------------------------------------ #
    # Operações de escrita
    # ------------------------------------------------------------------ #
    def append_row(self, sheet_name: str, row_values: List[Any]) -> None:
        def _do():
            self._service.spreadsheets().values().append(
                spreadsheetId=settings.GOOGLE_SHEET_ID,
                range=f"{sheet_name}!A:Z",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [row_values]},
            ).execute()

        self._with_retry(_do)

    def update_row(self, sheet_name: str, row_number: int, row_values: List[Any]) -> None:
        """Atualiza uma linha específica (row_number é 1-indexed, incluindo o header)."""

        def _do():
            self._service.spreadsheets().values().update(
                spreadsheetId=settings.GOOGLE_SHEET_ID,
                range=f"{sheet_name}!A{row_number}",
                valueInputOption="USER_ENTERED",
                body={"values": [row_values]},
            ).execute()

        self._with_retry(_do)

    def ensure_headers(self, sheet_name: str, headers: List[str]) -> None:
        """Garante que a primeira linha da aba tenha os cabeçalhos corretos."""

        def _do():
            result = (
                self._service.spreadsheets()
                .values()
                .get(spreadsheetId=settings.GOOGLE_SHEET_ID, range=f"{sheet_name}!A1:Z1")
                .execute()
            )
            existing = result.get("values", [[]])
            if not existing or existing[0] != headers:
                self._service.spreadsheets().values().update(
                    spreadsheetId=settings.GOOGLE_SHEET_ID,
                    range=f"{sheet_name}!A1",
                    valueInputOption="USER_ENTERED",
                    body={"values": [headers]},
                ).execute()

        self._with_retry(_do)


# Instância única usada em toda a aplicação
sheets_service = GoogleSheetsService()

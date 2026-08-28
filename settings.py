"""
Configurações centrais da aplicação.
Todos os valores sensíveis vêm do .env e NUNCA são expostos ao frontend.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-insegura-troque-isso")
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"

    GOOGLE_CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "")
    GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")

    # Nomes das abas dentro da planilha (a "estrutura do banco de dados")
    SHEET_PRODUTOS = "Produtos"
    SHEET_VENDAS = "Vendas"
    SHEET_MOVIMENTACOES = "Movimentacoes"
    SHEET_CONFIGURACOES = "Configuracoes"

    # Cabeçalhos esperados em cada aba (ordem importa)
    HEADERS = {
        SHEET_PRODUTOS: [
            "ID", "Produto", "Categoria", "Custo", "PrecoVenda",
            "EstoqueInicial", "EstoqueAtual", "EstoqueMinimo", "Ativo",
        ],
        SHEET_VENDAS: [
            "IDVenda", "Data", "ProdutoID", "Produto", "Quantidade",
            "ValorUnitario", "Total", "CustoUnitario", "Lucro",
        ],
        SHEET_MOVIMENTACOES: [
            "ID", "Data", "ProdutoID", "Tipo", "Quantidade", "Motivo", "Usuario",
        ],
        SHEET_CONFIGURACOES: ["Chave", "Valor"],
    }

    # Escopo mínimo necessário para ler/escrever na planilha
    GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


settings = Settings()

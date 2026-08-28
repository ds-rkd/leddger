# Ledger — Gestão de Vendas, Estoque e Financeiro

Sistema web para controlar vendas, estoque e indicadores financeiros de uma
pequena operação, usando o **Google Sheets como banco de dados**.

- **Backend:** Python + Flask, arquitetura em camadas (routes → services → Google Sheets)
- **Frontend:** HTML5 + CSS3 + JavaScript (SPA leve, sem frameworks pesados)
- **Banco de dados:** Google Sheets, via Google Sheets API v4
- **Gráficos:** Chart.js

---

## 1. Estrutura do projeto

```text
project/
├── app.py                   # cria e configura o Flask app
├── requirements.txt
├── .env.example              # copie para .env e preencha
├── scripts_init_sheets.py    # cria os cabeçalhos das abas na planilha
├── config/
│   └── settings.py           # configurações centrais (lidas do .env)
├── routes/                   # endpoints REST (Blueprints do Flask)
│   ├── dashboard.py
│   ├── products.py
│   ├── sales.py
│   ├── inventory.py
│   └── reports.py
├── services/                  # regras de negócio + integração Google
│   ├── google_sheets.py       # ÚNICO ponto de contato com a API do Google
│   ├── sales_service.py
│   ├── inventory_service.py
│   └── analytics_service.py
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/{app,dashboard,products,sales,charts}.js
```

---

## 2. Estrutura da planilha (Google Sheets)

Crie uma planilha com 4 abas, exatamente com estes nomes e cabeçalhos
(o script `scripts_init_sheets.py` cria os cabeçalhos automaticamente,
mas as abas em si precisam existir antes):

**Produtos**
`ID | Produto | Categoria | Custo | PrecoVenda | EstoqueInicial | EstoqueAtual | EstoqueMinimo | Ativo`

**Vendas**
`IDVenda | Data | ProdutoID | Produto | Quantidade | ValorUnitario | Total | CustoUnitario | Lucro`

**Movimentacoes**
`ID | Data | ProdutoID | Tipo | Quantidade | Motivo | Usuario`

**Configuracoes**
`Chave | Valor`

---

## 3. Configurando o Google Cloud (passo a passo)

1. Acesse [console.cloud.google.com](https://console.cloud.google.com) e crie um novo projeto (ou use um existente).
2. No menu **APIs e serviços → Biblioteca**, procure por **Google Sheets API** e clique em **Ativar**.
3. Vá em **APIs e serviços → Credenciais → Criar credenciais → Conta de serviço**.
4. Dê um nome à conta de serviço (ex: `ledger-sheets`) e conclua a criação. Não é necessário conceder papéis de projeto.
5. Abra a conta de serviço criada → aba **Chaves** → **Adicionar chave → Criar nova chave → JSON**.
   Isso baixa um arquivo `.json` — guarde-o com cuidado, ele é a credencial de acesso.
6. Copie esse arquivo para dentro do projeto, por exemplo em `credentials/service_account.json`.
7. Abra o arquivo `.json` baixado e copie o valor do campo `client_email`
   (algo como `ledger-sheets@seu-projeto.iam.gserviceaccount.com`).
8. Abra sua planilha do Google Sheets → botão **Compartilhar** → cole esse e-mail
   e conceda permissão de **Editor**. Sem esse passo, a API não conseguirá escrever na planilha.
9. Pegue o **Spreadsheet ID** na URL da planilha:
   `https://docs.google.com/spreadsheets/d/ESTE_TRECHO_É_O_ID/edit`

---

## 4. Configurando o `.env`

```bash
cp .env.example .env
```

Edite o `.env`:

```env
GOOGLE_CREDENTIALS_FILE=credentials/service_account.json
GOOGLE_SHEET_ID=cole_aqui_o_id_da_planilha
SECRET_KEY=gere-uma-string-aleatoria-longa
FLASK_ENV=development
```

---

## 5. Instalação e execução

```bash
# 1. Crie um ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Crie os cabeçalhos nas abas da planilha (rode uma vez)
python scripts_init_sheets.py

# 4. Inicie o servidor
python app.py
```

Acesse **http://localhost:5000**.

---

## 6. Como utilizar

1. Cadastre seus produtos em **Produtos** (custo, preço de venda, estoque inicial e mínimo).
2. Registre vendas na tela **Vendas** — o sistema valida o estoque disponível antes de confirmar.
3. Acompanhe faturamento, lucro e alertas de estoque no **Dashboard**, filtrando por período.
4. Ajuste entradas/saídas manuais de estoque em **Estoque**, com motivo obrigatório (fica no histórico de auditoria).
5. Veja produtos mais rentáveis e exporte um CSV em **Relatórios**.
6. Em **Configurações**, confira se a conexão com o Google Sheets está ativa.

---

## 7. Solução de problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| "Google Sheets · Desconectado" | `.env` incompleto ou credencial inválida | Confira `GOOGLE_CREDENTIALS_FILE` e `GOOGLE_SHEET_ID` |
| Erro `PERMISSION_DENIED` | Planilha não compartilhada com a service account | Compartilhe a planilha com o `client_email` do JSON, como Editor |
| Erro `Unable to parse range` | Nome da aba diferente do esperado | As abas devem se chamar exatamente `Produtos`, `Vendas`, `Movimentacoes`, `Configuracoes` |
| "Estoque insuficiente" ao vender | Estoque atual menor que a quantidade pedida | Ajuste o estoque em **Estoque → Ajustar estoque** |
| Mudanças na planilha não aparecem | Cache do navegador | Recarregue a página — o sistema busca a planilha a cada carregamento de página/filtro |

---

## 8. Notas sobre consistência de dados

O Google Sheets não é um banco transacional. Para reduzir o risco de
inconsistência, cada venda é tratada como duas etapas monitoradas:
1. a venda é gravada na aba `Vendas`;
2. o estoque do produto é então decrementado.

Se a etapa 2 falhar (ex: perda de conexão), o sistema **avisa explicitamente**
com o ID da venda para que o estoque seja conferido e ajustado manualmente —
em vez de falhar silenciosamente ou duplicar dados.

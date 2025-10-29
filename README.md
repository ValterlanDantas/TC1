Tech Challenge — Books API (Web Scraping + API Pública)

Desafio: Criação de uma API Pública para consulta de livros a partir de dados extraídos do site books.toscrape.com.
Objetivo: entregar pipeline completo (ingestão → transformação → API) pensando em escalabilidade e reuso para cenários de ML.

✅ Entregáveis

Repositório Organizado

Estrutura modular: src/tc_01/{api,routers,core,data,dashboard}, scripts/, data/.

README completo (este arquivo).

Web Scraping

Script automatizado extraindo todos os livros.

Campos: title, price, rating, availability, category, image.

Dados salvos em CSV (src/tc_01/data/books_data.csv).

API RESTful (FastAPI)

Endpoints core e opcionais (listados abaixo).

Swagger (OpenAPI) automático.

Monitoramento & Analytics

Logs estruturados de chamadas.

Métricas de performance via endpoint dedicado.

Dashboard simples com Streamlit.

🧱 Arquitetura & Pipeline
[books.toscrape.com] --(scraping)--> [CSV local: books_data.csv]
      |                                            |
      +---------------------> [ETL leve] <---------+
                                     |
                                     v
                            [FastAPI - API pública]
                                     |
                +--------------------+---------------------+
                |                                          |
         [Clientes externos]                       [Dashboard - Streamlit]
                |                                          |
        (consomem endpoints)                      (lê LOG_FILE com métricas)


Escalabilidade futura: trocar CSV por DB (Postgres), adicionar cache (Redis) e observabilidade (JSONL/ELK).

ML-ready: endpoints estáveis para features/datasets de treino (quando habilitados).

📦 Estrutura do Projeto
src/
  tc_01/
    api/
      main.py                # App FastAPI, routers, carga do CSV
    routers/
      books.py               # Endpoints core (+ price-range opcional)
      categories.py          # Lista/contagem de categorias
      auth.py                # Login JWT
      admin.py               # Rotas administrativas (ex.: trigger scraping)
      metrics.py             # Métricas processadas a partir dos logs
    core/
      security.py            # JWT / dependências de auth
      logs.py                # Middleware com logs estruturados em arquivo texto
    data/
      books_data.csv         # Dataset (resultado do scraping)
    dashboard/
      app.py                 # Streamlit – monitoramento & analytics
scripts/
  scraping.py                # (exemplo) job de scraping
pyproject.toml               # Dependências
README.md                    # Este arquivo

🔧 Instalação & Execução (local)
Pré-requisitos

Python 3.11+

Virtualenv recomendado

Windows (PowerShell):

python -m venv .venv
.\.venv\Scripts\Activate.ps1


Linux/macOS (bash):

python -m venv .venv
source .venv/bin/activate

Dependências (pyproject)

No pyproject.toml, garanta estas libs:

dependencies = [
  "requests>=2.32.0,<3.0.0",
  "beautifulsoup4>=4.12,<5.0",
  "fastapi>=0.112,<1.0",
  "uvicorn[standard]>=0.30,<1.0",
  "PyJWT>=2.9,<3.0",
  "pandas>=2.0",
  "streamlit>=1.37",
  "altair==5.3.0",
  "typing_extensions>=4.12",
]


Instale:

pip install -U pip
pip install fastapi "uvicorn[standard]" PyJWT requests beautifulsoup4 pandas streamlit "altair==5.3.0" "typing_extensions>=4.12"

Variáveis de Ambiente (importante)

Use o mesmo LOG_FILE para a API e para o dashboard.

Windows (PowerShell):

$env:PYTHONPATH = ".\src"
$env:LOG_FILE   = (Resolve-Path ".\api_logs.log").Path


Linux/macOS (bash):

export PYTHONPATH=./src
export LOG_FILE=$(realpath ./api_logs.log)

Rodando a API (dev)
python -m uvicorn src.tc_01.api.main:app --reload


Swagger: http://127.0.0.1:8000/docs

OpenAPI JSON: http://127.0.0.1:8000/openapi.json

🔐 Autenticação (JWT)

Login: POST /api/v1/auth/login
Credenciais de demo (apenas dev): {"username":"admin", "password":"admin123"}

Resposta:

{ "access_token": "<JWT>", "token_type": "bearer" }


Use o token nas chamadas: Authorization: Bearer <JWT>

📚 Endpoints Core
GET /api/v1/health

Verifica status da API e conectividade.

Ex: GET /api/v1/health

GET /api/v1/books

Lista livros com paginação e ordenação.

Query params: page (1), page_size (20), sort (ex.: rating_desc,price_asc)
Campos: id, title, price, rating

Ex: GET /api/v1/books?page=1&page_size=20&sort=rating_desc,price_asc

GET /api/v1/books/{id}

Livro por ID.

Ex: GET /api/v1/books/1

GET /api/v1/books/search

Busca por título e/ou categoria (contains, case-insensitive), com paginação/ordenação.

Query params: title, category, page, page_size, sort

Ex: GET /api/v1/books/search?title=travel&category=History

GET /api/v1/categories

Lista categorias com contagem.

🧠 Endpoints Opcionais (Insights)
GET /api/v1/stats/overview

Estatísticas gerais (total, preço médio/mín/máx, distribuição de rating, etc.).

GET /api/v1/stats/categories

Métricas por categoria (quantidade, estoque, preço médio/mín/máx, rating médio).

GET /api/v1/books/price-range

Filtra por faixa de preço (com paginação).

Query params: min, max, page, page_size

Ex: GET /api/v1/books/price-range?min=10&max=50&page=1&page_size=20

📈 Métricas, Logs & Dashboard

Logs estruturados (middleware) gravados em LOG_FILE:

2025-10-28 19:29:05,013 - INFO - GET /api/v1/health status=200 0.042s


Endpoint de métricas: GET /api/v1/metrics/overview

Total de requisições

Tempo médio

Top endpoints

Taxa de erro (4xx/5xx)

Dashboard (Streamlit)

Arquivo: src/tc_01/dashboard/app.py
Mostra:

Volume por endpoint

Latência média por minuto

Proporção por classe HTTP (2xx/4xx/5xx)

Tabela com últimas requisições

Rodar:

streamlit run src/tc_01/dashboard/app.py


Dica: confirme que LOG_FILE aponta para o mesmo arquivo usado pela API.

🧪 Plano de Testes (local)

Autenticação

POST /api/v1/auth/login (credenciais de demo) → recebe access_token.

Requisição sem Authorization em rota protegida → 401.

Health

GET /api/v1/health → 200 OK.

Listagem de livros

GET /api/v1/books?page=1&page_size=20 → 200, 20 itens, campos esperados.

sort=rating_desc,price_asc → ordenação aplicada.

Busca

GET /api/v1/books/search?title=travel → itens contendo “travel” em title.

GET /api/v1/books/search?category=History.

Por ID

GET /api/v1/books/1 → item válido.

GET /api/v1/books/999999 → 404.

Categorias

GET /api/v1/categories → lista e contagens corretas.

Insights

GET /api/v1/stats/overview e GET /api/v1/stats/categories → sem exceções, valores numéricos.

Price Range

GET /api/v1/books/price-range?min=10&max=50 → preços no intervalo.

Métricas & Dashboard

Execute algumas rotas para gerar logs → verifique GET /api/v1/metrics/overview.

Abra o Streamlit e valide gráficos/KPIs.

🧰 Troubleshooting

Token inválido: InvalidSignatureError
Refaça o login e use o novo access_token no header Authorization: Bearer.

Dashboard vazio
Verifique LOG_FILE. Gere tráfego (chame algumas rotas) e recarregue o Streamlit.

Erro Altair/TypedDict (closed=...)
Garanta: altair==5.3.0 e typing_extensions>=4.12.

ImportError tc_01
Exporte PYTHONPATH=./src antes de subir a API.

👥 Créditos

Autores: ver pyproject.toml.

Base de dados: books.toscrape.com (site de demonstração).
# 📚 Books API – Tech Challenge Fase 1  
**Machine Learning Engineering – Pós Tech | FIAP**  

API pública e painel interativo para consulta e monitoramento de livros.  
O projeto foi containerizado com **Docker** e implantado na nuvem via **Render**, oferecendo:  
- **API REST (FastAPI)** com endpoints de livros, categorias e métricas;  
- **Dashboard (Streamlit)** para análise de tráfego e desempenho da API.  

---

##  Tecnologias utilizadas
- **Python 3.11**
- **FastAPI** — backend REST
- **Uvicorn** — servidor ASGI
- **Streamlit** — dashboard web
- **Pandas / Altair** — análise e visualização de dados
- **Docker / Docker Compose** — containerização
- **Render.com** — deploy cloud

---
## Arquitetura 
### Main flow as a user
 Usuário -> Swagger -> API -> GET bookstoscrape -> response 200
![alt text](<docs/tc1-User flow.drawio.png>)

### Main flow API as a client

API as a client -> API -> Webscraping on BooksToScrap -> Armazena o .csv no filesystem do container -> http response 200

![alt text](<docs/tc1-API use flow.drawio.png>)

### Arquitetura Futura (Escalabilidade)

![alt text](<docs/tc1-Escalabilidade diagrama.drawio.png>)

## ⚙️ Estrutura do projeto
```
TC1/
├── src/
│   └── tc_01/
│       ├── api/
│       │   └── main.py
│       ├── routers/
│       │   ├── books.py
│       │   ├── categories.py
│       │   └── metrics.py   ← endpoints /overview e /entries
│       ├── core/
│       │   └── logs.py      ← middleware de log das requisições
│       ├── scripts/
│       │   └── scraping.py
│       └── dashboard/
│           └── app.py       ← Streamlit dashboard
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

---

## 🧩 Funcionalidades principais

### API (FastAPI)
- `/api/v1/books` → lista de livros  
- `/api/v1/categories` → categorias disponíveis  
- `/api/v1/metrics/overview` → estatísticas agregadas (total, top endpoints, erro médio, etc.)  
- `/api/v1/metrics/entries` → logs detalhados (timestamp, método, path, status, latência)

### Dashboard (Streamlit)
- KPIs: total de requisições, latência média, P95, taxa de erro  
- Top endpoints por volume  
- Latência média ao longo do tempo  
- Proporção de respostas por classe HTTP  
- Tabela com últimas requisições  
- Atualização automática a cada **30 segundos**

---

## 🧰 Como rodar localmente com Docker

### Pré-requisitos
- Docker e Docker Compose instalados.

### Passos
```bash
# Build e execução dos serviços
docker compose up --build
```

Acesse:
- **API** → http://localhost:8000/docs  
- **Dashboard** → http://localhost:8501  

### Variáveis de ambiente (já configuradas no docker-compose)
```yaml
# serviço API
PYTHONPATH=src
SECRET_KEY=dev-secret
ACCESS_TOKEN_EXPIRE_MIN=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# serviço Dashboard
PYTHONPATH=/app/src
API_BASE_URL=http://tc01_api:8000
METRICS_ENDPOINT=/api/v1/metrics/overview
METRICS_ENTRIES=/api/v1/metrics/entries
```

---


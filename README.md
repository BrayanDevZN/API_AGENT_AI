# DataPilot AI Agent API

API responsavel pela camada inteligente do DataPilot. Ela recebe perguntas do usuario, consulta a API de contas para validar identidade e historico, interpreta datasets com apoio de IA, executa transformacoes com pandas e devolve respostas, graficos e sugestoes analiticas para o frontend.

## Visao geral

O `AI AGENT` e o servico de inteligencia da plataforma. Ele nao armazena usuarios nem dashboards diretamente; essa responsabilidade fica na API `DATABASE`. O agente atua como um orquestrador analitico:

- valida o token do usuario na API de contas;
- recupera historico de conversa quando necessario;
- interpreta prompts de chat e de dashboard;
- limpa e perfila dados tabulares;
- gera planos de graficos com IA;
- executa agregacoes de dados com pandas;
- cria insights em linguagem natural;
- chama a API de contas para salvar dashboards gerados.

## Tecnologias

| Tecnologia | Uso no projeto |
| --- | --- |
| Python | Linguagem principal da API |
| FastAPI | Framework HTTP, definicao das rotas e validacao de entrada |
| Uvicorn | Servidor ASGI usado em desenvolvimento e deploy |
| Pydantic | Schemas de request/response |
| OpenAI API | Interpretacao de prompts e geracao de textos analiticos |
| pandas | Limpeza, agrupamento, agregacao e preparacao dos dados |
| python-dotenv | Carregamento de configuracoes locais |
| requests | Integracao com a API de contas/dados |
| StreamingResponse | Resposta incremental em NDJSON para status de geracao |

## Arquitetura

```text
Cliente / Frontend
      |
      v
api/routes.py
      |
      v
app/manager.py
      |
      v
app/service.py
      |
      +--> app/accounts_client.py  -> API DATABASE
      +--> app/interpreter.py      -> OpenAI interpreta pedido/plano
      +--> app/data_cleaner.py     -> Normalizacao do dataset
      +--> app/data_profiler.py    -> Perfil das colunas
      +--> app/pandas_tools.py     -> Operacoes tabulares
      +--> app/analyzer.py         -> Graficos simples/legados
      +--> app/generator.py        -> Respostas e insights
```

### Responsabilidades por camada

| Camada | Arquivos | Responsabilidade |
| --- | --- | --- |
| Entrada HTTP | `api/routes.py` | Expõe rotas, recebe JSON/FormData, trata erros e retorna respostas HTTP |
| Schemas | `api/model.py` | Define contratos Pydantic para chat e dashboards |
| Orquestracao | `app/manager.py`, `app/service.py` | Coordena validacao, historico, IA, pandas e persistencia externa |
| Integracao externa | `app/accounts_client.py` | Chama a API `DATABASE` para validar token, buscar fontes e salvar dashboards |
| Inteligencia | `app/interpreter.py`, `app/generator.py` | Usa OpenAI para interpretar prompts e gerar analises |
| Dados | `app/data_cleaner.py`, `app/data_profiler.py`, `app/pandas_tools.py`, `app/analyzer.py` | Limpa, descreve, agrega e estrutura dados para graficos |
| Configuracao | `core/config.py` | Carrega variaveis de ambiente |

## Fluxos principais

### Chat

```text
POST /chat
  -> valida token na API DATABASE
  -> busca mensagens da conversa
  -> envia pergunta + historico para o generator
  -> retorna answer
```

### Geracao de dashboard

```text
POST /dashboard/analyze
  -> recebe token, titulo, prompt e data_source_id
  -> busca a fonte de dados na API DATABASE
  -> limpa e perfila o dataset
  -> cria plano de graficos com IA
  -> executa agregacoes com pandas
  -> gera analise textual
  -> salva dashboard e graficos na API DATABASE
  -> retorna dashboard, charts, ai_suggestion e plan
```

### Atualizacao de dashboard

```text
POST /dashboard/refresh/analyze
  -> busca novamente a fonte de dados
  -> recalcula plano, graficos e sugestao
  -> retorna dados para o frontend/API DATABASE salvar via /dashboard/refresh/finish
```

## Estrutura de pastas

```text
AI AGENT/
├── api/
│   ├── model.py
│   └── routes.py
├── app/
│   ├── accounts_client.py
│   ├── analyzer.py
│   ├── data_cleaner.py
│   ├── data_profiler.py
│   ├── file_reader.py
│   ├── generator.py
│   ├── interpreter.py
│   ├── manager.py
│   ├── pandas_tools.py
│   └── service.py
├── core/
│   └── config.py
├── tests/
│   └── test_dashboard_prompt_compaction.py
├── main.py
├── requirements.txt
└── README.md
```

## Variaveis de ambiente

Crie um arquivo `.env` em `core/.env` ou configure as variaveis no ambiente de deploy.

| Variavel | Obrigatoria | Padrao | Descricao |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | Sim | - | Chave da OpenAI usada pelo interpreter/generator |
| `OPENAI_MODEL` | Nao | `gpt-4o-mini` | Modelo usado para interpretacao e geracao |
| `ACCOUNTS_API_URL` | Sim | - | URL base da API `DATABASE` |
| `ENV` | Nao | `dev` | Ambiente de execucao |
| `DEBUG` | Nao | `false` | Habilita informacoes de debug |
| `TIMEOUT` | Nao | `10` | Timeout padrao para chamadas externas |
| `MAX_HISTORY_MESSAGES` | Nao | `10` | Limite de mensagens usadas como contexto |
| `MAX_ROWS` | Nao | `1000` | Limite de linhas considerado nos fluxos legados |

## Como executar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## Rotas

### `POST /chat`

Conversa com a IA usando o historico de uma conversa salva na API de contas.

Body JSON:

```json
{
  "token": "JWT_DO_USUARIO",
  "conversation_id": 1,
  "question": "Quais insights posso tirar dos meus dados?"
}
```

Resposta:

```json
{
  "answer": "Resposta em linguagem natural gerada pela IA."
}
```

### `POST /dashboard/analyze`

Gera um dashboard completo a partir de uma fonte de dados ja cadastrada na API `DATABASE`.

Content-Type: `multipart/form-data`

Campos:

| Campo | Tipo | Obrigatorio | Descricao |
| --- | --- | --- | --- |
| `token` | string | Sim | JWT do usuario |
| `title` | string | Sim | Nome do dashboard |
| `prompt` | string | Nao | Instrucao de analise |
| `data_source_id` | integer | Sim | ID da fonte de dados |

Resposta:

```json
{
  "dashboard": {
    "id": 10,
    "title": "Vendas por categoria"
  },
  "charts": [
    {
      "title": "Receita por categoria",
      "chart_type": "bar",
      "x": "categoria",
      "y": "receita",
      "data": []
    }
  ],
  "ai_suggestion": "Analise textual gerada pela IA.",
  "plan": {}
}
```

### `POST /dashboard/analyze/stream`

Mesma finalidade de `/dashboard/analyze`, mas responde em `application/x-ndjson` com eventos incrementais.

Eventos possiveis:

```json
{ "type": "status", "message": "Carregando fonte de dados." }
{ "type": "status", "message": "Gerando graficos e analise com IA." }
{ "type": "complete", "data": {} }
{ "type": "error", "message": "Mensagem de erro." }
```

Use esta rota no frontend quando quiser exibir progresso durante geracoes demoradas.

### `POST /dashboard/refresh/analyze`

Recalcula graficos e analise textual para um dashboard existente. A rota nao salva o resultado final; ela retorna a nova analise para ser persistida pela API de contas.

Content-Type: `multipart/form-data`

Campos iguais a `/dashboard/analyze`.

Resposta:

```json
{
  "charts": [],
  "ai_suggestion": "Nova analise gerada pela IA.",
  "plan": {}
}
```

## Tipos de graficos suportados

O agente trabalha com os seguintes tipos:

| Tipo | Uso |
| --- | --- |
| `bar` | Comparacao entre categorias |
| `horizontal_bar` | Ranking horizontal |
| `line` | Serie temporal |
| `area` | Evolucao acumulada/visual |
| `pie` | Participacao percentual |
| `donut` | Participacao percentual em anel |
| `scatter` | Relacao entre variaveis numericas |
| `table` | Tabela com linhas do dataset |
| `kpi` | Indicador numerico |

Operacoes de dados comuns:

- `groupby`
- `count`
- `time_groupby`
- `scatter`
- `kpi`
- `table`

Agregacoes suportadas:

- `sum`
- `mean`
- `count`
- `max`
- `min`
- `median`
- `none`

## Integracao com outros servicos

| Servico | Direcao | Finalidade |
| --- | --- | --- |
| Frontend React | Recebe chamadas | Chat, criacao e atualizacao de dashboards |
| API DATABASE | Chamadas de saida | Validar token, buscar fontes, buscar historico e salvar dashboards |
| OpenAI API | Chamadas de saida | Interpretar prompts e gerar textos |

## Testes

Existe teste automatizado para compactacao de prompt de dashboards:

```bash
pytest
```

## Observacoes de producao

- A API nao deve receber secrets no body alem do JWT do usuario.
- O endpoint de streaming deve ser consumido linha a linha como NDJSON.
- Datasets muito grandes sao compactados antes de serem enviados para IA.
- Calculos numericos ficam em pandas; a IA decide o plano e explica o resultado.
- Erros de payload grande sao convertidos em mensagem amigavel para o frontend.

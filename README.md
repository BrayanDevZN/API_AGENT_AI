# DataPilot AI Agent API

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-Responses_API-412991?style=for-the-badge&logo=openai&logoColor=white)](https://platform.openai.com/docs)
[![Polars](https://img.shields.io/badge/Polars-DataFrames-CD792C?style=for-the-badge&logo=polars&logoColor=white)](https://pola.rs/)
[![Pydantic](https://img.shields.io/badge/Pydantic-Validation-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-499848?style=for-the-badge&logo=gunicorn&logoColor=white)](https://www.uvicorn.org/)
[![Pytest](https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)

API de inteligencia artificial do DataPilot. Este servico transforma fontes de dados cadastradas em dashboards, graficos e analises executivas usando uma arquitetura que combina FastAPI, OpenAI, Polars, validacao forte com Pydantic e integracao com a API de contas/dados da plataforma.

O objetivo do projeto e resolver um problema real de produto: permitir que uma pessoa suba uma fonte de dados, faca uma pergunta em linguagem natural e receba um dashboard persistido, com graficos coerentes, dados agregados e uma narrativa de BI pronta para tomada de decisao.

## Indice

- [Visao geral](#visao-geral)
- [Arquitetura](#arquitetura)
- [Tecnologias](#tecnologias)
- [Principais capacidades](#principais-capacidades)
- [Fluxos da API](#fluxos-da-api)
- [Rotas](#rotas)
- [Contratos de graficos](#contratos-de-graficos)
- [Variaveis de ambiente](#variaveis-de-ambiente)
- [Como executar](#como-executar)
- [Testes](#testes)
- [Seguranca e confiabilidade](#seguranca-e-confiabilidade)
- [Estrutura de pastas](#estrutura-de-pastas)

## Visao geral

O `AI AGENT` e o microservico responsavel pela camada inteligente do DataPilot. Ele nao e apenas um wrapper de LLM: a IA decide o plano analitico, mas os calculos de dados ficam em codigo deterministico com Polars. Esse desenho reduz alucinacao numerica, melhora a consistencia dos graficos e deixa o resultado mais confiavel para uso em dashboards reais.

Responsabilidades principais:

- Validar o JWT do usuario na API de contas.
- Buscar historico de conversa para respostas de chat.
- Buscar fontes de dados ja cadastradas na API `DATABASE`.
- Limpar datasets tabulares antes da analise.
- Criar perfil de colunas, tipos, nulos, amostras e valores unicos.
- Usar OpenAI para planejar dashboards com base no schema real.
- Normalizar o plano retornado pela IA para impedir colunas inventadas.
- Executar agregacoes, filtros, rankings, series temporais, KPIs e tabelas com Polars.
- Gerar uma analise executiva em portugues com recomendacoes praticas.
- Persistir dashboards e graficos criados na API de contas/dados.
- Oferecer endpoint de streaming NDJSON para feedback de progresso no frontend.

## Arquitetura

```text
Frontend React
    |
    | HTTP / FormData / JSON
    v
FastAPI - main.py
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
    |       |                        /valid_token
    |       |                        /conversation/messages
    |       |                        /data-source
    |       |                        /dashboard/create
    |       |                        /dashboard/chart/create
    |
    +--> app/data_cleaner.py     -> limpeza de dataset
    +--> app/data_profiler.py    -> inferencia de schema
    +--> app/interpreter.py      -> plano analitico com OpenAI
    +--> app/polars_tools.py     -> calculos deterministas
    +--> app/generator.py        -> narrativa executiva com OpenAI
    +--> app/analyzer.py         -> fluxo analitico legado/simples
```

### Decisoes de arquitetura

| Decisao | Impacto tecnico |
| --- | --- |
| Separacao entre planejamento por IA e calculo em Polars | A IA escolhe a intencao analitica, mas os numeros sao calculados de forma reproduzivel. |
| Integracao com a API `DATABASE` via `AccountsClient` | O agente fica stateless em relacao a usuarios, fontes e dashboards. |
| Schemas Pydantic nas rotas | Requests invalidos falham antes de chegar na regra de negocio. |
| Compactacao de payload antes de chamar IA | Datasets grandes continuam usaveis sem enviar linhas desnecessarias para o modelo. |
| Normalizacao defensiva do plano de graficos | Evita graficos com IDs, emails, URLs ou colunas tecnicas como metricas de negocio. |
| Streaming NDJSON | O frontend consegue mostrar progresso durante geracoes demoradas. |

## Tecnologias

| Tecnologia | Uso no projeto |
| --- | --- |
| Python | Linguagem principal da API. |
| FastAPI | Framework HTTP, definicao das rotas, CORS e validacao de entrada. |
| Uvicorn | Servidor ASGI para desenvolvimento e deploy. |
| Pydantic | Contratos dos payloads de chat e dashboard. |
| OpenAI Responses API | Interpretacao de prompts, planejamento analitico e geracao da narrativa. |
| Polars | Limpeza, filtros, agregacoes, series temporais, KPIs e tabelas. |
| Requests | Comunicacao HTTP com a API `DATABASE`. |
| python-dotenv | Carregamento de variaveis a partir de `core/.env`. |
| Pytest / unittest | Testes de compactacao de prompt e coerencia semantica do plano. |
| FastAPI StreamingResponse | Resposta incremental em `application/x-ndjson`. |

## Principais capacidades

- **Chat contextual:** responde perguntas usando o historico de uma conversa salva.
- **Dashboard automatico:** cria dashboard persistido a partir de uma fonte ja cadastrada.
- **Atualizacao de dashboard:** recalcula graficos e insights para uma fonte atualizada.
- **Planejamento semantico:** classifica colunas como metricas, dimensoes, datas ou campos tecnicos.
- **Fallback robusto:** se a IA retornar plano ruim, o interpretador tenta corrigir ou cria graficos seguros.
- **Drill-down:** adiciona hierarquia exploravel quando existe relacao real entre colunas.
- **Filtros por linguagem natural:** transforma pedidos como "apenas aprovados" em filtros usando valores reais do dataset.
- **Analise executiva:** gera resumo, indicadores, descobertas, tendencias, alertas, recomendacoes e proximos passos.
- **Protecao contra payload grande:** compacta schema, valores unicos, linhas e planos antes das chamadas ao modelo.

## Fluxos da API

### 1. Chat

```text
POST /chat
    -> valida token na API DATABASE
    -> busca mensagens da conversa
    -> monta prompt com historico
    -> chama OpenAI
    -> retorna answer
```

### 2. Geracao de dashboard

```text
POST /dashboard/analyze
    -> recebe token, titulo, prompt e data_source_id
    -> busca a fonte em /data-source
    -> valida dataset
    -> limpa dados com DataCleaner
    -> cria perfil com DataProfiler
    -> gera plano com Interpreter.dashboard_plan
    -> normaliza plano e remove escolhas ruins
    -> executa dados com PolarsTools
    -> gera narrativa com Generator.dashboard_analysis_multi
    -> salva dashboard em /dashboard/create
    -> salva graficos em /dashboard/chart/create
    -> retorna dashboard, charts, ai_suggestion e plan
```

### 3. Geracao com progresso

```text
POST /dashboard/analyze/stream
    -> emite status: carregando fonte
    -> executa o mesmo fluxo de /dashboard/analyze
    -> emite complete com o resultado final
    -> em caso de erro, emite error
```

### 4. Refresh de dashboard

```text
POST /dashboard/refresh/analyze
    -> busca a fonte atualizada
    -> recalcula plano, graficos e narrativa
    -> nao salva dashboard diretamente
    -> retorna dados para outro servico persistir o refresh
```

## Rotas

### `POST /chat`

Conversa com a IA usando uma conversa ja existente na API de contas.

**Content-Type:** `application/json`

**Body:**

```json
{
  "token": "JWT_DO_USUARIO",
  "conversation_id": 1,
  "question": "Explique como interpretar um grafico de dispersao."
}
```

**Resposta:**

```json
{
  "answer": "Resposta gerada pela IA em linguagem natural."
}
```

**Validacoes:**

- `token` e obrigatorio e nao pode ser vazio.
- `conversation_id` precisa ser maior que zero.
- `question` e obrigatoria e nao pode ser vazia.
- O token precisa ser aceito pela API `DATABASE`.

### `POST /dashboard/analyze`

Gera e salva um dashboard completo a partir de uma fonte de dados ja cadastrada.

**Content-Type:** `multipart/form-data`

| Campo | Tipo | Obrigatorio | Descricao |
| --- | --- | --- | --- |
| `token` | string | Sim | JWT do usuario autenticado. |
| `title` | string | Sim | Nome do dashboard que sera salvo. |
| `prompt` | string | Nao | Pedido especifico do usuario. Se vazio, a API gera uma analise geral. |
| `data_source_id` | integer | Sim | ID da fonte de dados na API `DATABASE`. |

**Exemplo com cURL:**

```bash
curl -X POST "http://localhost:8001/dashboard/analyze" \
  -F "token=JWT_DO_USUARIO" \
  -F "title=Dashboard Comercial" \
  -F "prompt=Mostre os principais indicadores de vendas" \
  -F "data_source_id=1"
```

**Resposta:**

```json
{
  "dashboard": {
    "id": 10,
    "title": "Dashboard Comercial"
  },
  "charts": [
    {
      "id": 77,
      "dashboard_id": 10,
      "chart_type": "horizontal_bar",
      "title": "Total de Receita por Categoria",
      "chart_data": {
        "data": [
          {
            "Categoria": "Enterprise",
            "Receita": 92000
          }
        ]
      },
      "chart_config": {
        "x": "Categoria",
        "y": "Receita",
        "aggregation": ["sum"],
        "operation": "groupby",
        "filters": [],
        "drill_down": {
          "enabled": false
        },
        "reason": "Compara a receita total entre categorias."
      }
    }
  ],
  "ai_suggestion": "Analise executiva gerada pela IA.",
  "plan": {
    "tool": "dashboard_plan",
    "dataset_type": "vendas",
    "analysis_type": "specific"
  }
}
```

### `POST /dashboard/analyze/stream`

Gera e salva um dashboard, mas envia eventos incrementais para o frontend.

**Content-Type:** `multipart/form-data`

Usa os mesmos campos de `/dashboard/analyze`.

**Media type da resposta:** `application/x-ndjson`

**Eventos:**

```json
{"type":"status","message":"Carregando fonte de dados."}
{"type":"status","message":"Gerando graficos e analise com IA."}
{"type":"complete","data":{"dashboard":{},"charts":[],"ai_suggestion":"","plan":{}}}
```

**Evento de erro:**

```json
{"type":"error","message":"ValueError: Fonte de dados nao encontrada."}
```

Esse endpoint e ideal para telas em que a geracao pode demorar e o usuario precisa acompanhar o progresso.

### `POST /dashboard/refresh/analyze`

Recalcula os graficos e a analise de um dashboard a partir da fonte atualizada. Diferente de `/dashboard/analyze`, esse endpoint nao cria um novo dashboard e nao persiste graficos diretamente.

**Content-Type:** `multipart/form-data`

| Campo | Tipo | Obrigatorio | Descricao |
| --- | --- | --- | --- |
| `token` | string | Sim | JWT do usuario autenticado. |
| `title` | string | Sim | Titulo usado no contexto da analise. |
| `prompt` | string | Nao | Pedido especifico ou prompt original do dashboard. |
| `data_source_id` | integer | Sim | Fonte usada para recalcular os dados. |

**Resposta:**

```json
{
  "charts": [
    {
      "index": 1,
      "title": "Total de Receita por Mes",
      "chart_type": "line",
      "operation": "time_groupby",
      "x": "label",
      "y": "value",
      "aggregation": ["sum"],
      "filters": [],
      "drill_down": {
        "enabled": false
      },
      "reason": "Mostra a evolucao da receita no tempo.",
      "plan": {},
      "data": []
    }
  ],
  "ai_suggestion": "Nova analise executiva gerada pela IA.",
  "plan": {
    "tool": "dashboard_plan"
  }
}
```

## Contratos de graficos

### Tipos suportados

| Tipo | Quando usar |
| --- | --- |
| `bar` | Comparacao entre poucas categorias. |
| `horizontal_bar` | Rankings, nomes longos ou muitas categorias. |
| `line` | Evolucao temporal. |
| `area` | Evolucao visual de volume ou acumulado. |
| `pie` | Participacao percentual com poucas categorias. |
| `donut` | Participacao percentual em formato de anel. |
| `scatter` | Relacao entre duas metricas numericas. |
| `table` | Amostra tabular ou detalhes. |
| `kpi` | Indicador unico e direto. |
| `none` | Sem grafico aplicavel. |

### Operacoes suportadas

| Operacao | Descricao |
| --- | --- |
| `groupby` | Agrupa uma metrica numerica por uma dimensao categorica. |
| `count` | Conta registros por categoria. |
| `time_groupby` | Agrega metricas por dia, semana, mes, trimestre ou ano. |
| `scatter` | Retorna pares numericos para correlacao visual. |
| `kpi` | Calcula um unico indicador agregado. |
| `table` | Retorna as primeiras linhas do dataset filtrado. |

### Agregacoes suportadas

| Agregacao | Significado |
| --- | --- |
| `sum` | Soma. |
| `mean` | Media. |
| `count` | Contagem. |
| `max` | Maior valor. |
| `min` | Menor valor. |
| `median` | Mediana. |
| `none` | Sem agregacao, usado em tabela ou dispersao. |

### Frequencias temporais

| Valor | Periodo |
| --- | --- |
| `D` | Dia. |
| `W` | Semana. |
| `M` | Mes. |
| `Q` | Trimestre. |
| `Y` | Ano. |

### Filtros

Os filtros sao aplicados por `PolarsTools.filter_dataframe`.

```json
{
  "column": "Status",
  "operator": "equals",
  "value": "APROVADO"
}
```

Operadores:

- `equals`
- `not_equals`
- `contains`
- `in`

## Variaveis de ambiente

As variaveis sao carregadas de `core/.env` ou do ambiente do deploy.

| Variavel | Obrigatoria | Padrao | Descricao |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | Sim | - | Chave usada para chamar a OpenAI. |
| `OPENAI_MODEL` | Nao | `gpt-4o-mini` | Modelo usado no planejamento e na geracao textual. |
| `ACCOUNTS_API_URL` | Sim | - | URL base da API `DATABASE`. |
| `ENV` | Nao | `dev` | Nome do ambiente. |
| `DEBUG` | Nao | `false` | Flag de debug. |
| `TIMEOUT` | Nao | `10` | Timeout das chamadas externas em segundos. |
| `MAX_HISTORY_MESSAGES` | Nao | `10` | Limite configuravel de mensagens de contexto. |
| `MAX_ROWS` | Nao | `1000` | Limite configuravel para fluxos legados. |

Exemplo:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
ACCOUNTS_API_URL=http://localhost:8000
ENV=dev
DEBUG=false
TIMEOUT=10
MAX_HISTORY_MESSAGES=10
MAX_ROWS=1000
```

## Como executar

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

Depois de iniciar, a documentacao interativa fica disponivel em:

```text
http://localhost:8001/docs
```

### Dependencias externas para rodar localmente

- A API `DATABASE` precisa estar online e acessivel por `ACCOUNTS_API_URL`.
- O usuario precisa enviar um JWT valido.
- A fonte de dados precisa existir na API `DATABASE`.
- `OPENAI_API_KEY` precisa estar configurada.

## Testes

O projeto possui testes focados nos pontos mais sensiveis do agente: compactacao de payload para IA e normalizacao semantica do plano de graficos.

```bash
pytest
```

Coberturas importantes:

- O drill-down completo fica disponivel para persistencia, mas e removido do payload enviado a IA.
- Valores unicos sao limitados antes de entrar no prompt.
- Planos ruins vindos da IA sao corrigidos para usar colunas de negocio.
- Graficos repetidos por dimensao sao deduplicados.
- Titulos sao normalizados para refletir metrica, dimensao e agregacao reais.

## Seguranca e confiabilidade

- O agente valida o JWT na API `DATABASE` antes de acessar historico ou fontes.
- O servico nao persiste usuarios, senhas ou fontes diretamente.
- A IA nao calcula os numeros finais dos graficos; os calculos sao feitos por Polars.
- O plano de dashboard e sanitizado antes da execucao.
- Colunas tecnicas como IDs, emails, URLs e telefones sao evitadas como metricas de negocio.
- Payloads grandes sao compactados para reduzir custo, latencia e risco de exceder limite.
- Erros conhecidos de payload grande sao convertidos em mensagem amigavel para o frontend.
- CORS esta limitado aos ambientes locais do frontend e ao dominio do DataPilot.

## Estrutura de pastas

```text
AI AGENT/
|-- api/
|   |-- model.py
|   `-- routes.py
|-- app/
|   |-- accounts_client.py
|   |-- analyzer.py
|   |-- data_cleaner.py
|   |-- data_profiler.py
|   |-- file_reader.py
|   |-- generator.py
|   |-- interpreter.py
|   |-- manager.py
|   |-- polars_tools.py
|   `-- service.py
|-- core/
|   `-- config.py
|-- tests/
|   |-- test_dashboard_plan_semantics.py
|   `-- test_dashboard_prompt_compaction.py
|-- main.py
|-- requirements.txt
`-- README.md
```

## Resumo tecnico para recrutadores

Este projeto demonstra uma arquitetura de IA aplicada a dados com separacao clara entre orquestracao, integracao, planejamento, processamento e geracao textual. O ponto central nao e apenas chamar um modelo: o servico usa a IA para interpretar intencao e produzir um plano, valida esse plano contra o schema real, executa os calculos com Polars e devolve um dashboard persistivel com narrativa de negocio.

Em termos praticos, a API resolve desafios comuns de sistemas com IA em producao: controle de payload, consistencia numerica, validacao defensiva, streaming de progresso, integracao entre microservicos e degradacao segura quando a resposta do modelo nao vem perfeita.

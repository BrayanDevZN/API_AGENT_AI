<div align="center">

# 🤖 AI Data Analysis API

**Agente inteligente de análise de dados com conversa contextual**



</div>



## 🧠 Sobre o projeto

A **AI Data Analysis API** é um backend inteligente que combina **modelos de linguagem** com **análise de dados via pandas** para oferecer uma experiência conversacional sobre qualquer dataset.

Ela foi projetada para **separar responsabilidades** de forma clara: a IA interpreta intenções e gera respostas em linguagem natural, enquanto o pandas executa os cálculos. Isso reduz custo de tokens, aumenta precisão e facilita manutenção.

> ⚠️ **A API não renderiza gráficos.** Ela retorna apenas a estrutura de dados para que o frontend construa a visualização.

---

## ✨ Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| 💬 **Conversa contextual** | Mantém histórico por usuário e conversa |
| 🔍 **Interpretação de intenção** | Identifica automaticamente o que o usuário quer analisar |
| 📊 **Análise de datasets** | Processa dados com pandas (sum, mean, count, max, min) |
| 📈 **Estrutura de gráficos** | Gera o schema de dados para o frontend renderizar |
| 💡 **Insights automáticos** | Produz conclusões e recomendações em linguagem natural |
| 📁 **Upload de arquivos** | Aceita CSV, Excel e JSON diretamente |
| 🔐 **Autenticação JWT** | Valida identidade do usuário em cada requisição |

---

## 🏗️ Arquitetura

### Fluxo da aplicação

```
Usuário
   ↓
Routes         → valida entrada HTTP, recebe arquivos
   ↓
Service        → orquestra o fluxo, valida JWT, busca histórico
   ↓
Interpreter    → entende a intenção: chat ou análise?
   ↓
Analyzer*      → processa dataset com pandas (*apenas se análise)
   ↓
Generator      → gera resposta natural ou insights via IA
   ↓
Resposta final
```

### Módulos

```
📦 projeto/
├── main.py            # Inicialização da API e registro de rotas
├── routes.py          # Camada HTTP (endpoints, validação de entrada)
├── service.py         # Orquestrador principal (JWT, histórico, fluxo)
├── interpreter.py     # Interpretador de intenção (chat vs análise)
├── analyzer.py        # Motor analítico com pandas
├── generator.py       # Geração de respostas e insights via IA
├── file_reader.py     # Leitura de CSV, Excel e JSON → list[dict]
└── accounts_client.py # Cliente da API externa de autenticação
```

#### Detalhes de cada módulo

<details>
<summary><strong>service.py</strong> — Cérebro da aplicação</summary>

Responsável por orquestrar todo o fluxo:
1. Valida o token JWT
2. Busca o histórico de mensagens do usuário
3. Chama o `interpreter` para entender a intenção
4. Decide se aciona o `analyzer`
5. Chama o `generator` para montar a resposta final

</details>

<details>
<summary><strong>interpreter.py</strong> — Interpretador de intenção</summary>

Recebe a pergunta do usuário e decide:
- É conversa comum ou análise de dados?
- Qual tipo de gráfico usar?
- Quais colunas do dataset são relevantes?
- Qual agregação aplicar?

Exemplo de saída:
```json
{
  "chart_type": "bar",
  "x": "produto",
  "y": "vendas",
  "aggregation": "sum",
  "mode": "analysis"
}
```

</details>

<details>
<summary><strong>analyzer.py</strong> — Motor analítico</summary>

Processa o dataset usando **pandas**. A IA **não faz cálculos** — ela apenas interpreta e comunica. Toda a matemática fica aqui.

Operações suportadas: `sum`, `mean`, `count`, `max`, `min`

</details>

<details>
<summary><strong>generator.py</strong> — Geração de linguagem natural</summary>

Dois modos de operação:
- **chat**: responde conversas comuns, sem gráfico
- **analysis**: explica resultados, gera insights e sugestões

</details>

<details>
<summary><strong>file_reader.py</strong> — Leitor de arquivos</summary>

Suporta `.csv`, `.xlsx`, `.xls` e `.json`.  
Sempre retorna no formato padronizado `list[dict]` usado internamente.

</details>

---

## 🛠️ Tecnologias

| Tecnologia | Uso |
|---|---|
| **FastAPI** | Framework web assíncrono |
| **OpenAI API** | Interpretação e geração de linguagem natural |
| **pandas** | Processamento e agregação de dados |
| **Pydantic** | Validação de schemas de entrada |
| **Railway** | Deploy e infraestrutura em nuvem |
| **JWT** | Autenticação stateless |
| **Requests** | Integração com API de contas externa |
| **Python Multipart** | Suporte a upload de arquivos |

---

## 🌐 Rotas da API

**URL Base:** `https://web-production-40ead.up.railway.app`

---

### `POST /analyze/json`

Conversa ou análise enviando os dados diretamente no body.

**Body:**
```json
{
  "token": "JWT_DO_USUARIO",
  "conversation_id": 1,
  "question": "qual produto vende mais?",
  "dataset": [
    { "produto": "Mouse",   "vendas": 100 },
    { "produto": "Teclado", "vendas": 200 }
  ]
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `token` | string | JWT do usuário |
| `conversation_id` | int | ID da conversa |
| `question` | string | Pergunta em linguagem natural |
| `dataset` | list[dict] | Dados para análise (pode ser vazio) |

**Resposta:**
```json
{
  "answer": "O produto Teclado possui maior volume de vendas...",
  "chart": {
    "type": "bar",
    "x": "produto",
    "y": "vendas",
    "data": [
      { "produto": "Mouse",   "vendas": 100 },
      { "produto": "Teclado", "vendas": 200 }
    ]
  },
  "interpretation": {
    "chart_type": "bar",
    "x": "produto",
    "y": "vendas",
    "aggregation": "sum",
    "mode": "analysis"
  }
}
```

---

### `POST /analyze/file`

Análise com upload de arquivo (CSV, Excel ou JSON).

**FormData:**

| Campo | Tipo |
|---|---|
| `file` | arquivo (.csv, .xlsx, .xls, .json) |
| `token` | string |
| `conversation_id` | int |
| `question` | string |

---

## 💡 Exemplos de uso

### Conversa simples

```javascript
async function chat() {
  const response = await fetch(
    "https://web-production-40ead.up.railway.app/analyze/json",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        token: "SEU_JWT",
        conversation_id: 1,
        question: "oi",
        dataset: []
      })
    }
  );

  const data = await response.json();

  console.log(data);
}

chat();
```

---

### Análise de vendas por produto

```javascript
async function analyzeSales() {
  const response = await fetch(
    "https://web-production-40ead.up.railway.app/analyze/json",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        token: "SEU_JWT",
        conversation_id: 1,
        question: "qual produto vende mais?",
        dataset: [
          { produto: "Mouse", vendas: 100 },
          { produto: "Teclado", vendas: 200 },
          { produto: "Monitor", vendas: 350 }
        ]
      })
    }
  );

  const data = await response.json();

  console.log(data);
}

analyzeSales();
```

---

### Análise via upload de arquivo

```javascript
async function uploadFile(file) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("token", "SEU_JWT");
  formData.append("conversation_id", 1);
  formData.append("question", "qual produto vende mais?");

  const response = await fetch(
    "https://web-production-40ead.up.railway.app/analyze/file",
    {
      method: "POST",
      body: formData
    }
  );

  const data = await response.json();

  console.log(data);
}
```
---

## ⚙️ Modos de operação

### 💬 Modo Chat

Ativado quando não há dataset ou a pergunta é uma conversa comum.

```
Entrada:  "oi, tudo bem?"
Saída:    resposta conversacional, sem gráfico
```

### 📊 Modo Analysis

Ativado quando há dataset e a pergunta exige análise de dados.

```
Entrada:  "qual produto tem maior margem de lucro?" + dataset
Saída:    insight em linguagem natural + estrutura de gráfico
```

---

## 📊 Tipos de gráfico e agregações

### Tipos de gráfico

| Tipo | Uso ideal |
|---|---|
| `bar` | Ranking e comparação entre categorias |
| `line` | Evolução temporal de uma métrica |
| `pie` | Proporção e distribuição percentual |
| `scatter` | Correlação entre duas variáveis numéricas |
| `none` | Sem gráfico (modo chat) |

### Agregações suportadas

| Tipo | Operação |
|---|---|
| `sum` | Soma dos valores |
| `mean` | Média dos valores |
| `count` | Contagem de registros |
| `max` | Maior valor |
| `min` | Menor valor |
| `none` | Sem agregação |

---

## 🖥️ Responsabilidade do frontend

A API retorna apenas dados estruturados. Cabe ao frontend:

- [ ] Enviar a pergunta e o dataset (JSON ou arquivo)
- [ ] **Renderizar o gráfico** com base no campo `chart` da resposta
- [ ] Exibir o texto do campo `answer`
- [ ] Gerenciar autenticação e obter o JWT

---

## 🚀 Evolução futura

A arquitetura foi projetada para crescer. Próximas possibilidades:

- 🗄️ **Agentes SQL** — consultas diretas a bancos de dados
- 📉 **Detecção de anomalias** — identificação de outliers automaticamente
- 🔮 **Previsões** — modelos de forecasting integrados
- 🧠 **Memória longa** — contexto persistente entre sessões
- 📚 **RAG** — respostas baseadas em documentos e bases de conhecimento
- 📊 **Dashboards inteligentes** — geração automática de painéis

---

<div align="center">

Feito com ☕ e **FastAPI** · [Voltar ao topo](#-ai-data-analysis-api)

</div>

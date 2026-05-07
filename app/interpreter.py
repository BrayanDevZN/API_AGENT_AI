import json
from openai import OpenAI
from core.config import settings


class Interpreter:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def run(
        self,
        question: str,
        columns: list[str],
        messages: list
    ) -> dict:

        if not columns:
            prompt = self._chat_prompt(
                question=question,
                messages=messages
            )
        else:
            prompt = self._analysis_prompt(
                question=question,
                columns=columns,
                messages=messages
            )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        return self._safe_json(response.output_text)

    def _chat_prompt(self, question: str, messages: list) -> str:
        return f"""
Você é um interpretador de intenção.

Neste momento NÃO existe dataset disponível.
Então sua função NÃO é criar análise de dados.
Sua função é identificar que a pergunta deve ser tratada como conversa normal.

Responda SOMENTE em JSON válido.
Não use markdown.
Não explique.
Não escreva texto fora do JSON.

Formato obrigatório:

{{
  "chart_type": "none",
  "x": null,
  "y": null,
  "aggregation": "none",
  "mode": "chat",
  "reason": "sem_dataset"
}}

Regras:
- Como não existe dataset, SEMPRE use chart_type "none".
- Como não existem colunas, SEMPRE use x null e y null.
- Como não há dados para agregar, SEMPRE use aggregation "none".
- Não invente colunas.
- Não tente criar gráfico.
- Não tente inferir dados pelo histórico.
- Mesmo que o usuário peça gráfico, responda como sem_dataset.

Pergunta do usuário:
{question}

Histórico:
{json.dumps(messages, ensure_ascii=False)}
"""

    def _analysis_prompt(
        self,
        question: str,
        columns: list[str],
        messages: list
    ) -> str:
        return f"""
Você é um interpretador especialista em análise de dados.

Sua função é transformar a pergunta do usuário em uma estrutura JSON que será usada por um sistema Python com pandas.

Responda SOMENTE em JSON válido.
Não use markdown.
Não explique.
Não escreva texto fora do JSON.

Formato obrigatório:

{{
  "chart_type": "bar | line | pie | scatter | none",
  "x": "nome_da_coluna_ou_null",
  "y": "nome_da_coluna_ou_null",
  "aggregation": "sum | mean | count | max | min | none",
  "mode": "analysis | chat",
  "reason": "explicacao_curta"
}}

Regras gerais:
- Use apenas colunas existentes na lista de colunas disponíveis.
- Não invente colunas.
- Não altere nomes das colunas.
- Se uma coluna tiver acento, espaço ou letra maiúscula, copie exatamente como está.
- Se a pergunta não for sobre análise de dados, use chart_type "none" e mode "chat".
- Se a pergunta for ambígua ou impossível com as colunas existentes, use chart_type "none".
- Se faltar uma coluna necessária para responder, use chart_type "none".
- O campo reason deve ser curto e objetivo.

Tipos de gráfico:
- "bar": comparação entre categorias, ranking, maiores/menores, total por grupo.
- "line": evolução no tempo, tendência, crescimento, queda por data.
- "pie": proporção, participação percentual, distribuição simples.
- "scatter": relação entre duas variáveis numéricas.
- "none": conversa comum, pergunta impossível, falta de dados ou falta de colunas.

Agregações:
- "count": contar registros, frequência, quantidade por categoria.
- "sum": somar valores.
- "mean": calcular média.
- "max": maior valor.
- "min": menor valor.
- "none": sem agregação.

Regras para escolher x:
- x normalmente é a coluna categórica ou temporal.
- Para ranking por produto, x deve ser produto.
- Para vendas por cidade, x deve ser cidade.
- Para evolução no tempo, x deve ser data.
- Para contagem por categoria, x deve ser a categoria.

Regras para escolher y:
- y normalmente é a coluna numérica.
- Para soma, média, máximo ou mínimo, y deve ser uma coluna numérica.
- Para count, y deve ser null.
- Se não existir coluna numérica adequada, use chart_type "none".

Exemplos:

Pergunta:
"qual produto vendeu mais?"

Resposta:
{{
  "chart_type": "bar",
  "x": "produto",
  "y": "vendas",
  "aggregation": "sum",
  "mode": "analysis",
  "reason": "ranking_por_produto"
}}

Pergunta:
"quantos clientes existem por cidade?"

Resposta:
{{
  "chart_type": "bar",
  "x": "cidade",
  "y": null,
  "aggregation": "count",
  "mode": "analysis",
  "reason": "contagem_por_categoria"
}}

Pergunta:
"qual foi a evolução das vendas por mês?"

Resposta:
{{
  "chart_type": "line",
  "x": "mes",
  "y": "vendas",
  "aggregation": "sum",
  "mode": "analysis",
  "reason": "evolucao_temporal"
}}

Pergunta:
"qual a porcentagem de vendas por região?"

Resposta:
{{
  "chart_type": "pie",
  "x": "regiao",
  "y": "vendas",
  "aggregation": "sum",
  "mode": "analysis",
  "reason": "proporcao_por_categoria"
}}

Pergunta:
"oi, tudo bem?"

Resposta:
{{
  "chart_type": "none",
  "x": null,
  "y": null,
  "aggregation": "none",
  "mode": "chat",
  "reason": "conversa_comum"
}}

Pergunta do usuário:
{question}

Colunas disponíveis:
{json.dumps(columns, ensure_ascii=False)}

Histórico:
{json.dumps(messages, ensure_ascii=False)}
"""

    def _safe_json(self, output_text: str) -> dict:
        try:
            data = json.loads(output_text)

            chart_type = data.get("chart_type", "none")
            x = data.get("x")
            y = data.get("y")
            aggregation = data.get("aggregation", "none")
            mode = data.get("mode", "chat")
            reason = data.get("reason", "")

            valid_chart_types = ["bar", "line", "pie", "scatter", "none"]
            valid_aggregations = ["sum", "mean", "count", "max", "min", "none"]
            valid_modes = ["analysis", "chat"]

            if chart_type not in valid_chart_types:
                chart_type = "none"

            if aggregation not in valid_aggregations:
                aggregation = "none"

            if mode not in valid_modes:
                mode = "chat"

            if chart_type == "none":
                x = None
                y = None
                aggregation = "none"

            if aggregation == "count":
                y = None

            return {
                "chart_type": chart_type,
                "x": x,
                "y": y,
                "aggregation": aggregation,
                "mode": mode,
                "reason": reason
            }

        except Exception:
            return {
                "chart_type": "none",
                "x": None,
                "y": None,
                "aggregation": "none",
                "mode": "chat",
                "reason": "json_invalido"
            }
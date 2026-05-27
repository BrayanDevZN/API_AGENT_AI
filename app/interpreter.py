import json
from openai import OpenAI
from core.config import settings


class Interpreter:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def run(self, question: str, columns: list[str], messages: list) -> dict:
        if not columns:
            prompt = self._chat_prompt(question=question, messages=messages)
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

    def dashboard_plan(self, prompt: str, schema: dict) -> dict:
        system_prompt = """
Você é um planejador de análise de dados.

Sua função é escolher uma operação pandas simples para gerar um gráfico.
Você receberá o pedido do usuário e o schema do dataset.

Responda SOMENTE em JSON válido.
Não use markdown.
Não explique.

Formato obrigatório:
{
  "operation": "groupby | count | time_groupby",
  "group_by": "nome_da_coluna_ou_null",
  "metric": "nome_da_coluna_ou_null",
  "aggregation": "sum | mean | count | max | min",
  "chart_type": "bar | line | pie | scatter",
  "title": "Título do gráfico",
  "x": "coluna_eixo_x",
  "y": "coluna_eixo_y",
  "time_column": "coluna_de_data_ou_null",
  "time_freq": "D | M | Y"
}

REGRAS:
- Use apenas colunas existentes no schema.
- Não invente colunas.
- Não altere o nome das colunas.
- Se uma coluna tiver acento, espaço, underline ou letra maiúscula, copie exatamente como está.
- Para "mais usado", "mais comum", "mais frequente", "quantidade por", "contagem por", use aggregation "count".
- aggregation "count" pode ser usada em colunas de texto/categoria.
- Para count, metric deve ser null.
- Para count, group_by deve ser a coluna categórica analisada.
- Para ranking, comparação ou total por categoria com valor numérico, use operation "groupby".
- Para quantidade por categoria sem valor numérico, use operation "count".
- Para análise por tempo, mês, dia, ano, evolução, tendência, período ou data, use operation "time_groupby".
- Para time_groupby, use uma coluna de data em time_column.
- Para análise mensal, use time_freq "M".
- Para análise diária, use time_freq "D".
- Para análise anual, use time_freq "Y".
- Para evolução temporal, use chart_type "line".
- Para proporção, use chart_type "pie".
- Para comparação comum, use chart_type "bar".
"""

        user_prompt = f"""
Pedido do usuário:
{prompt}

Schema:
{json.dumps(schema, ensure_ascii=False)}
"""

        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return self._safe_dashboard_plan(response.output_text)

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

Pergunta do usuário:
{question}

Histórico:
{json.dumps(messages, ensure_ascii=False)}
"""

    def _analysis_prompt(self, question: str, columns: list[str], messages: list) -> str:
        return f"""
Você é um interpretador especialista em análise de dados.

Responda SOMENTE em JSON válido.
Não use markdown.

Formato obrigatório:
{{
  "chart_type": "bar | line | pie | scatter | none",
  "x": "nome_da_coluna_ou_null",
  "y": "nome_da_coluna_ou_null",
  "aggregation": "sum | mean | count | max | min | none",
  "mode": "analysis | chat",
  "reason": "explicacao_curta"
}}

Regras:
- Use apenas colunas existentes.
- Não invente colunas.
- Para count, y deve ser null.
- Se for conversa comum, use chart_type "none".

Pergunta:
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

            if chart_type not in ["bar", "line", "pie", "scatter", "none"]:
                chart_type = "none"

            if aggregation not in ["sum", "mean", "count", "max", "min", "none"]:
                aggregation = "none"

            if mode not in ["analysis", "chat"]:
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

    def _safe_dashboard_plan(self, output_text: str) -> dict:
        try:
            data = json.loads(output_text)

            operation = data.get("operation", "count")
            aggregation = data.get("aggregation", "count")
            chart_type = data.get("chart_type", "bar")
            time_freq = data.get("time_freq", "M")

            if operation not in ["groupby", "count", "time_groupby"]:
                operation = "count"

            if aggregation not in ["sum", "mean", "count", "max", "min"]:
                aggregation = "count"

            if chart_type not in ["bar", "line", "pie", "scatter"]:
                chart_type = "bar"

            if time_freq not in ["D", "M", "Y"]:
                time_freq = "M"

            if operation == "count":
                data["metric"] = None
                aggregation = "count"

            if operation == "time_groupby":
                chart_type = "line"

            return {
                "operation": operation,
                "group_by": data.get("group_by"),
                "metric": data.get("metric"),
                "aggregation": aggregation,
                "chart_type": chart_type,
                "title": data.get("title", "Dashboard gerado"),
                "x": data.get("x") or data.get("group_by") or "periodo",
                "y": data.get("y") or data.get("metric") or "count",
                "time_column": data.get("time_column"),
                "time_freq": time_freq
            }

        except Exception:
            return {
                "operation": "count",
                "group_by": None,
                "metric": None,
                "aggregation": "count",
                "chart_type": "bar",
                "title": "Dashboard gerado",
                "x": None,
                "y": "count",
                "time_column": None,
                "time_freq": "M"
            }
import json
from openai import OpenAI
from core.config import Settings


class Interpreter:
    def __init__(self):
        self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
        self.model = Settings.OPENAI_MODEL

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

Sua função é escolher operações pandas simples para gerar gráfico.
Você receberá o pedido do usuário e o schema do dataset.

Responda SOMENTE em JSON válido.
Não use markdown.
Não explique.

Formato obrigatório:
{
  "tool": "chart_plan | rename_columns",
  "operation": "groupby | count | time_groupby",
  "group_by": ["coluna_1", "coluna_2"],
  "metric": ["coluna_numerica_1", "coluna_numerica_2"],
  "aggregation": ["sum", "mean"],
  "chart_type": "bar | line | pie | scatter",
  "title": "Título do gráfico",
  "x": "coluna_eixo_x",
  "y": "coluna_eixo_y",
  "time_column": "coluna_de_data_ou_null",
  "time_freq": "D | M | Y",
  "rename_columns": {
    "nome_original": "Nome Mais Intuitivo"
  }
}

TOOLS DISPONÍVEIS:

1. chart_plan
Use quando precisar gerar gráfico/análise.

2. rename_columns
Use quando as colunas tiverem nomes ruins, técnicos, abreviados ou pouco intuitivos.
Exemplo:
{
  "tool": "rename_columns",
  "rename_columns": {
    "vlr_rec": "Receita",
    "qtd_conv": "Conversões",
    "dt_camp": "Data da Campanha"
  }
}

REGRAS GERAIS:
- Responda sempre no formato JSON obrigatório.
- Use apenas colunas existentes no schema.
- Não invente colunas.
- Se uma coluna tiver acento, espaço, underline ou letra maiúscula, copie exatamente como está.
- Você pode usar rename_columns para deixar os nomes mais claros.
- Após renomear colunas, use os nomes novos em x, y, group_by e metric.
- Se não precisar renomear, retorne "rename_columns": {}.
- group_by SEMPRE deve ser lista.
- metric SEMPRE deve ser lista.
- aggregation SEMPRE deve ser lista.
- group_by pode ter uma ou várias colunas.
- metric pode ter uma ou várias colunas.
- aggregation pode ter uma ou várias funções.
- Aggregations permitidas: sum, mean, count, max, min.

REGRAS DE GRÁFICO:
- Para "mais usado", "mais comum", "mais frequente", "quantidade por", "contagem por", use operation "count".
- Para count, metric deve ser [].
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
- Para relação entre duas variáveis numéricas, use chart_type "scatter".
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
  "reason": "sem_dataset",
  "rename_columns": {{}}
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
  "reason": "explicacao_curta",
  "rename_columns": {{
    "nome_original": "Nome Mais Intuitivo"
  }}
}}

Nova tool disponível:
- rename_columns

Use rename_columns quando as colunas tiverem nomes ruins, técnicos ou pouco intuitivos.

Exemplo:
{{
  "rename_columns": {{
    "vlr_total": "Receita Total",
    "qtd_vnd": "Quantidade Vendida",
    "dt_cmp": "Data da Campanha"
  }}
}}

Regras:
- Use apenas colunas existentes.
- Não invente colunas.
- Para count, y deve ser null.
- Se for conversa comum, use chart_type "none".
- Se não precisar renomear, retorne "rename_columns": {{}}.
- Após renomear colunas, use os nomes novos em x e y.

Pergunta:
{question}

Colunas disponíveis:
{json.dumps(columns, ensure_ascii=False)}

Histórico:
{json.dumps(messages, ensure_ascii=False)}
"""

    def _as_list(self, value):
        if value is None:
            return []

        if isinstance(value, list):
            return value

        return [value]

    def _safe_json(self, output_text: str) -> dict:
        try:
            data = json.loads(output_text)

            chart_type = data.get("chart_type", "none")
            x = data.get("x")
            y = data.get("y")
            aggregation = data.get("aggregation", "none")
            mode = data.get("mode", "chat")
            reason = data.get("reason", "")
            rename_columns = data.get("rename_columns", {})

            if chart_type not in ["bar", "line", "pie", "scatter", "none"]:
                chart_type = "none"

            if aggregation not in ["sum", "mean", "count", "max", "min", "none"]:
                aggregation = "none"

            if mode not in ["analysis", "chat"]:
                mode = "chat"

            if not isinstance(rename_columns, dict):
                rename_columns = {}

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
                "reason": reason,
                "rename_columns": rename_columns
            }

        except Exception:
            return {
                "chart_type": "none",
                "x": None,
                "y": None,
                "aggregation": "none",
                "mode": "chat",
                "reason": "json_invalido",
                "rename_columns": {}
            }

    def _safe_dashboard_plan(self, output_text: str) -> dict:
        try:
            data = json.loads(output_text)

            tool = data.get("tool", "chart_plan")
            operation = data.get("operation", "count")
            chart_type = data.get("chart_type", "bar")
            time_freq = data.get("time_freq", "M")
            rename_columns = data.get("rename_columns", {})

            group_by = self._as_list(data.get("group_by"))
            metric = self._as_list(data.get("metric"))
            aggregation = self._as_list(data.get("aggregation", "count"))

            if tool not in ["chart_plan", "rename_columns"]:
                tool = "chart_plan"

            if operation not in ["groupby", "count", "time_groupby"]:
                operation = "count"

            valid_aggregations = ["sum", "mean", "count", "max", "min"]
            aggregation = [
                agg for agg in aggregation
                if agg in valid_aggregations
            ]

            if not aggregation:
                aggregation = ["count"]

            if chart_type not in ["bar", "line", "pie", "scatter"]:
                chart_type = "bar"

            if time_freq not in ["D", "M", "Y"]:
                time_freq = "M"

            if not isinstance(rename_columns, dict):
                rename_columns = {}

            if operation == "count":
                metric = []
                aggregation = ["count"]

            if operation == "time_groupby":
                chart_type = "line"

            x = data.get("x")
            y = data.get("y")

            if not x:
                x = group_by[0] if group_by else "periodo"

            if not y:
                y = metric[0] if metric else "count"

            return {
                "tool": tool,
                "operation": operation,
                "group_by": group_by,
                "metric": metric,
                "aggregation": aggregation,
                "chart_type": chart_type,
                "title": data.get("title", "Dashboard gerado"),
                "x": x,
                "y": y,
                "time_column": data.get("time_column"),
                "time_freq": time_freq,
                "rename_columns": rename_columns
            }

        except Exception:
            return {
                "tool": "chart_plan",
                "operation": "count",
                "group_by": [],
                "metric": [],
                "aggregation": ["count"],
                "chart_type": "bar",
                "title": "Dashboard gerado",
                "x": None,
                "y": "count",
                "time_column": None,
                "time_freq": "M",
                "rename_columns": {}
            }
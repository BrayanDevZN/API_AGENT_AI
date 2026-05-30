import json
from openai import OpenAI
from core.config import Settings


class Interpreter:
    VALID_CHART_TYPES = [
        "bar",
        "horizontal_bar",
        "line",
        "area",
        "pie",
        "donut",
        "scatter",
        "table",
        "none",
    ]

    VALID_OPERATIONS = [
        "groupby",
        "count",
        "time_groupby",
    ]

    VALID_AGGREGATIONS = [
        "sum",
        "mean",
        "count",
        "max",
        "min",
    ]

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
                messages=messages,
            )

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        return self._safe_json(response.output_text)

    def dashboard_plan(self, prompt: str, schema: dict) -> dict:
        system_prompt = """
Você é um planejador especialista em análise de dados, BI e dashboards.

Sua função é transformar o pedido do usuário em um plano com UM OU MAIS gráficos.
Você receberá o pedido do usuário e o schema do dataset.

Responda SOMENTE em JSON válido.
Não use markdown.
Não explique fora do JSON.

Formato obrigatório:
{
  "tool": "dashboard_plan",
  "rename_columns": {
    "nome_original": "Nome Intuitivo"
  },
  "charts": [
    {
      "title": "Título do gráfico",
      "operation": "groupby | count | time_groupby",
      "group_by": ["coluna_1"],
      "metric": ["coluna_numerica_1"],
      "aggregation": ["sum"],
      "chart_type": "bar | horizontal_bar | line | area | pie | donut | scatter | table",
      "x": "coluna_eixo_x",
      "y": "coluna_eixo_y",
      "time_column": "coluna_de_data_ou_null",
      "time_freq": "D | M | Y",
      "reason": "motivo curto da escolha"
    }
  ]
}

REGRAS PARA rename_columns:
- Sempre retorne rename_columns.
- Use rename_columns para transformar nomes técnicos em nomes fáceis para clientes.
- Nunca use underline (_), hífen (-), sufixos técnicos ou nomes de banco.
- Nunca use nomes como valor_total_sum, receita_mean, quantidade_count, preco_max.
- Os nomes finais devem ser nomes normais em português.
- Use nomes curtos, claros e profissionais.
- Se o nome original já for bom, pode manter igual.
- Não altere o significado da coluna.
- Não invente colunas.
- As chaves de rename_columns devem ser EXATAMENTE os nomes originais existentes no schema.
- Os valores de rename_columns devem ser os nomes amigáveis.
- Depois de renomear, os gráficos devem usar os nomes novos em group_by, metric, x, y e time_column.

EXEMPLOS DE rename_columns:
{
  "Valor_Total": "Valor Total",
  "valor_total": "Valor Total",
  "Receita": "Receita",
  "Data_Venda": "Data da Venda",
  "Qtd": "Quantidade",
  "Quantidade": "Quantidade",
  "Preco": "Preço",
  "Preco_Unitario": "Preço Unitário",
  "Desconto_Medio": "Desconto Médio",
  "Campanha_Nome": "Campanha",
  "Nome_Produto": "Produto"
}

REGRAS GERAIS:
- Retorne no máximo 4 gráficos.
- Retorne pelo menos 1 gráfico quando houver dataset e pedido de análise.
- Use apenas colunas existentes no schema ou nomes novos definidos em rename_columns.
- Não invente colunas.
- Se uma coluna tiver acento, espaço, underline ou letra maiúscula, copie exatamente como está nas chaves de rename_columns.
- group_by SEMPRE deve ser lista.
- metric SEMPRE deve ser lista.
- aggregation SEMPRE deve ser lista.
- Cada gráfico deve responder uma parte útil do pedido do usuário.
- Evite gráficos repetidos com a mesma ideia.

REGRAS DE OPERAÇÃO:
- Para "mais vendido", "maior receita", "total por categoria", "ranking por valor", use groupby.
- Para "mais comum", "mais frequente", "quantidade por", "contagem por", use count.
- Para "evolução", "tendência", "por mês", "por dia", "por ano", use time_groupby.
- Para count, metric deve ser [] e aggregation deve ser ["count"].
- Para time_groupby, time_column deve ser uma coluna de data.
- Para análise mensal, use time_freq "M".
- Para análise diária, use time_freq "D".
- Para análise anual, use time_freq "Y".

REGRAS DE CHART_TYPE:
- bar: comparação comum entre categorias.
- horizontal_bar: ranking com nomes longos ou muitas categorias.
- line: evolução temporal.
- area: evolução temporal com volume acumulado ou tendência geral.
- pie: participação percentual com poucas categorias, no máximo 6.
- donut: participação percentual visual com poucas categorias, no máximo 6.
- scatter: relação entre duas variáveis numéricas.
- table: quando gráfico não for adequado ou quando o resultado for muito detalhado.

REGRAS PARA ESCOLHER VÁRIOS GRÁFICOS:
- Se o usuário pedir uma visão geral ou não enviar prompt específico, crie 2 a 4 gráficos complementares.
- Para vendas, considere:
  1. total por produto/categoria
  2. evolução no tempo se houver data
  3. participação por categoria
  4. ranking dos maiores valores
- Para campanhas, considere:
  1. receita por campanha
  2. conversões por campanha
  3. evolução por período
  4. média ou taxa se existir coluna adequada
- Para dados financeiros, considere:
  1. receita/despesa por categoria
  2. evolução temporal
  3. maiores valores
  4. participação percentual

IMPORTANTE:
- Não force gráfico de tempo se não existir coluna de data.
- Não use pie/donut com muitas categorias.
- Não use scatter se não existirem duas colunas numéricas.
- Para nomes muito longos no eixo X, prefira horizontal_bar.
"""

        user_prompt = f"""
Pedido do usuário:
{prompt if prompt and prompt.strip() else "Faça uma análise geral completa do dataset, como um analista de dados."}

Schema:
{json.dumps(schema, ensure_ascii=False)}
"""

        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
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
Não explique fora do JSON.

Formato obrigatório:
{{
  "chart_type": "bar | horizontal_bar | line | area | pie | donut | scatter | table | none",
  "x": "nome_da_coluna_ou_null",
  "y": "nome_da_coluna_ou_null",
  "aggregation": "sum | mean | count | max | min | none",
  "mode": "analysis | chat",
  "reason": "explicacao_curta",
  "rename_columns": {{
    "nome_original": "Nome Intuitivo"
  }}
}}

REGRAS PARA rename_columns:
- Sempre retorne rename_columns.
- Use nomes normais em português.
- Nunca use underline (_).
- Nunca use hífen (-).
- Nunca use nomes técnicos.
- Nunca use sufixos como sum, mean, count, max, min.
- As chaves devem ser exatamente nomes existentes nas colunas disponíveis.
- Os valores devem ser nomes amigáveis para cliente final.
- Depois de renomear, use os nomes novos em x e y.

Exemplos:
Valor_Total -> Valor Total
valor_total -> Valor Total
Quantidade -> Quantidade
Qtd -> Quantidade
Data_Venda -> Data da Venda
Preco_Unitario -> Preço Unitário
Campanha_Nome -> Campanha
Nome_Produto -> Produto

Regras:
- Use apenas colunas existentes ou nomes novos definidos em rename_columns.
- Não invente colunas.
- Para count, y deve ser null.
- Se for conversa comum, use chart_type "none".
- Para comparação comum, use bar.
- Para ranking com nomes longos, use horizontal_bar.
- Para evolução temporal, use line.
- Para tendência com volume ao longo do tempo, use area.
- Para participação percentual com poucas categorias, use pie ou donut.
- Para relação entre duas variáveis numéricas, use scatter.
- Quando gráfico não ajudar, use table.

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

            if chart_type not in self.VALID_CHART_TYPES:
                chart_type = "none"

            if aggregation not in [*self.VALID_AGGREGATIONS, "none"]:
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
                "rename_columns": rename_columns,
            }

        except Exception:
            return {
                "chart_type": "none",
                "x": None,
                "y": None,
                "aggregation": "none",
                "mode": "chat",
                "reason": "json_invalido",
                "rename_columns": {},
            }

    def _normalize_chart_plan(self, chart: dict, index: int) -> dict:
        operation = chart.get("operation", "count")
        chart_type = chart.get("chart_type", "bar")
        time_freq = chart.get("time_freq", "M")

        group_by = self._as_list(chart.get("group_by"))
        metric = self._as_list(chart.get("metric"))
        aggregation = self._as_list(chart.get("aggregation", "count"))

        if operation not in self.VALID_OPERATIONS:
            operation = "count"

        aggregation = [
            agg for agg in aggregation
            if agg in self.VALID_AGGREGATIONS
        ]

        if not aggregation:
            aggregation = ["count"]

        if chart_type not in self.VALID_CHART_TYPES:
            chart_type = "bar"

        if chart_type == "none":
            chart_type = "bar"

        if time_freq not in ["D", "M", "Y"]:
            time_freq = "M"

        if operation == "count":
            metric = []
            aggregation = ["count"]

        if operation == "time_groupby" and chart_type not in ["line", "area"]:
            chart_type = "line"

        x = chart.get("x")
        y = chart.get("y")

        if not x:
            x = group_by[0] if group_by else "periodo"

        if not y:
            y = metric[0] if metric else "count"

        title = chart.get("title") or f"Gráfico {index + 1}"

        return {
            "title": title,
            "operation": operation,
            "group_by": group_by,
            "metric": metric,
            "aggregation": aggregation,
            "chart_type": chart_type,
            "x": x,
            "y": y,
            "time_column": chart.get("time_column"),
            "time_freq": time_freq,
            "reason": chart.get("reason", ""),
        }

    def _safe_dashboard_plan(self, output_text: str) -> dict:
        try:
            data = json.loads(output_text)

            tool = data.get("tool", "dashboard_plan")
            rename_columns = data.get("rename_columns", {})

            if tool not in ["dashboard_plan", "rename_columns", "chart_plan"]:
                tool = "dashboard_plan"

            if tool == "chart_plan":
                tool = "dashboard_plan"

            if not isinstance(rename_columns, dict):
                rename_columns = {}

            raw_charts = data.get("charts")

            if not isinstance(raw_charts, list):
                raw_charts = [data]

            charts = [
                self._normalize_chart_plan(chart, index)
                for index, chart in enumerate(raw_charts[:4])
                if isinstance(chart, dict)
            ]

            if not charts:
                charts = [
                    {
                        "title": "Dashboard gerado",
                        "operation": "count",
                        "group_by": [],
                        "metric": [],
                        "aggregation": ["count"],
                        "chart_type": "bar",
                        "x": None,
                        "y": "count",
                        "time_column": None,
                        "time_freq": "M",
                        "reason": "fallback_sem_graficos",
                    }
                ]

            first_chart = charts[0]

            return {
                "tool": tool,
                "rename_columns": rename_columns,
                "charts": charts,

                "operation": first_chart["operation"],
                "group_by": first_chart["group_by"],
                "metric": first_chart["metric"],
                "aggregation": first_chart["aggregation"],
                "chart_type": first_chart["chart_type"],
                "title": first_chart["title"],
                "x": first_chart["x"],
                "y": first_chart["y"],
                "time_column": first_chart["time_column"],
                "time_freq": first_chart["time_freq"],
            }

        except Exception:
            fallback_chart = {
                "title": "Dashboard gerado",
                "operation": "count",
                "group_by": [],
                "metric": [],
                "aggregation": ["count"],
                "chart_type": "bar",
                "x": None,
                "y": "count",
                "time_column": None,
                "time_freq": "M",
                "reason": "json_invalido",
            }

            return {
                "tool": "dashboard_plan",
                "rename_columns": {},
                "charts": [fallback_chart],

                "operation": fallback_chart["operation"],
                "group_by": fallback_chart["group_by"],
                "metric": fallback_chart["metric"],
                "aggregation": fallback_chart["aggregation"],
                "chart_type": fallback_chart["chart_type"],
                "title": fallback_chart["title"],
                "x": fallback_chart["x"],
                "y": fallback_chart["y"],
                "time_column": fallback_chart["time_column"],
                "time_freq": fallback_chart["time_freq"],
            }
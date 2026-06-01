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
        "none",
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

        return self._safe_json(response.output_text, columns=columns)

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

REGRAS CRÍTICAS:
- Use apenas colunas existentes no schema.
- NÃO invente colunas.
- NÃO use coluna derivada que não exista, como ROI, lucro, margem, ticket médio, crescimento, receita_total, se ela não estiver no schema.
- Se o usuário pedir ROI e existir uma coluna ROI no schema, pode usar ROI.
- Se o usuário pedir ROI e NÃO existir ROI no schema, escolha uma coluna numérica existente parecida com resultado, valor, receita, conversões ou investimento.
- group_by SEMPRE deve ser lista.
- metric SEMPRE deve ser lista.
- aggregation SEMPRE deve ser lista.
- Para count, metric deve ser [] e aggregation deve ser ["count"].
- Para groupby, group_by deve conter uma coluna categórica existente.
- Para groupby, metric deve conter uma coluna numérica existente.
- Para time_groupby, time_column deve ser uma coluna de data existente.
- Se não souber qual coluna usar, escolha uma coluna real do schema. Nunca deixe group_by vazio em gráficos groupby.
- Retorne no máximo 4 gráficos.
- Retorne pelo menos 1 gráfico quando houver dataset e pedido de análise.

REGRAS PARA rename_columns:
- Sempre retorne rename_columns.
- As chaves de rename_columns devem ser EXATAMENTE os nomes originais existentes no schema.
- Os valores devem ser nomes amigáveis.
- Não altere o significado da coluna.
- Não invente colunas.
- IMPORTANTE: os gráficos devem usar os nomes originais do schema, NÃO os nomes renomeados.
- rename_columns é apenas para exibição visual, não para definir group_by, metric, x, y ou time_column.

REGRAS DE OPERAÇÃO:
- Para "mais vendido", "maior receita", "total por categoria", "ranking por valor", use groupby.
- Para "mais comum", "mais frequente", "quantidade por", "contagem por", use count.
- Para "evolução", "tendência", "por mês", "por dia", "por ano", use time_groupby.
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
- table: quando gráfico não for adequado.
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

        return self._safe_dashboard_plan(
            output_text=response.output_text,
            schema=schema,
        )

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

REGRAS:
- Use apenas colunas existentes em Colunas disponíveis.
- Não invente colunas.
- Não use métricas derivadas se elas não existirem.
- Se aggregation for count, y deve ser null.
- Se chart_type for diferente de none, x deve ser uma coluna existente.
- Se aggregation não for count, y deve ser uma coluna numérica existente.
- rename_columns é apenas para exibição. Use nomes originais em x e y.
- Se for conversa comum, use chart_type "none".

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
            return [item for item in value if item is not None and item != ""]

        return [value]

    def _normalize_name(self, value) -> str:
        return str(value).strip().lower()

    def _schema_columns(self, schema: dict) -> list[str]:
        if not isinstance(schema, dict):
            return []

        columns = schema.get("columns") or schema.get("colunas") or []

        if isinstance(columns, dict):
            return list(columns.keys())

        if isinstance(columns, list):
            result = []

            for item in columns:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    name = item.get("name") or item.get("column") or item.get("nome")
                    if name:
                        result.append(name)

            return result

        return []

    def _numeric_columns(self, schema: dict, columns: list[str]) -> list[str]:
        if not isinstance(schema, dict):
            return []

        possible_keys = [
            "numeric_columns",
            "numerical_columns",
            "numeric",
            "numericas",
            "numéricas",
        ]

        for key in possible_keys:
            values = schema.get(key)

            if isinstance(values, list):
                return [value for value in values if value in columns]

        typed_columns = schema.get("columns") or schema.get("colunas")

        if isinstance(typed_columns, list):
            result = []

            for item in typed_columns:
                if not isinstance(item, dict):
                    continue

                name = item.get("name") or item.get("column") or item.get("nome")
                dtype = str(item.get("type") or item.get("dtype") or "").lower()

                if name in columns and any(term in dtype for term in ["int", "float", "number", "numeric", "decimal"]):
                    result.append(name)

            return result

        return []

    def _categorical_columns(self, schema: dict, columns: list[str], numeric_columns: list[str]) -> list[str]:
        possible_keys = [
            "categorical_columns",
            "categoricas",
            "categóricas",
            "categories",
        ]

        if isinstance(schema, dict):
            for key in possible_keys:
                values = schema.get(key)

                if isinstance(values, list):
                    return [value for value in values if value in columns]

        numeric_set = set(numeric_columns)
        return [column for column in columns if column not in numeric_set]

    def _date_columns(self, schema: dict, columns: list[str]) -> list[str]:
        possible_keys = [
            "date_columns",
            "datetime_columns",
            "data_columns",
            "datas",
        ]

        if isinstance(schema, dict):
            for key in possible_keys:
                values = schema.get(key)

                if isinstance(values, list):
                    return [value for value in values if value in columns]

        result = []

        for column in columns:
            normalized = self._normalize_name(column)

            if any(term in normalized for term in ["data", "date", "dia", "mes", "mês", "ano"]):
                result.append(column)

        return result

    def _find_column(self, requested, columns: list[str]) -> str | None:
        if not requested:
            return None

        requested_name = self._normalize_name(requested)

        for column in columns:
            if self._normalize_name(column) == requested_name:
                return column

        return None

    def _first_existing(self, values, columns: list[str]) -> str | None:
        for value in self._as_list(values):
            found = self._find_column(value, columns)

            if found:
                return found

        return None

    def _preferred_column(self, columns: list[str], preferred_names: list[str]) -> str | None:
        for preferred in preferred_names:
            for column in columns:
                if self._normalize_name(column) == preferred:
                    return column

        for preferred in preferred_names:
            for column in columns:
                if preferred in self._normalize_name(column):
                    return column

        return columns[0] if columns else None

    def _safe_json(self, output_text: str, columns: list[str] | None = None) -> dict:
        columns = columns or []

        try:
            data = json.loads(output_text)

            chart_type = data.get("chart_type", "none")
            x = self._find_column(data.get("x"), columns)
            y = self._find_column(data.get("y"), columns)
            aggregation = data.get("aggregation", "none")
            mode = data.get("mode", "chat")
            reason = data.get("reason", "")
            rename_columns = data.get("rename_columns", {})

            if chart_type not in self.VALID_CHART_TYPES:
                chart_type = "none"

            if aggregation not in self.VALID_AGGREGATIONS:
                aggregation = "none"

            if mode not in ["analysis", "chat"]:
                mode = "chat"

            if not isinstance(rename_columns, dict):
                rename_columns = {}

            rename_columns = {
                original: friendly
                for original, friendly in rename_columns.items()
                if self._find_column(original, columns)
            }

            if chart_type == "none":
                x = None
                y = None
                aggregation = "none"

            if aggregation == "count":
                y = None

            if chart_type != "none" and not x and columns:
                x = columns[0]

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

    def _normalize_chart_plan(
        self,
        chart: dict,
        index: int,
        columns: list[str],
        numeric_columns: list[str],
        categorical_columns: list[str],
        date_columns: list[str],
    ) -> dict:
        operation = chart.get("operation", "groupby")
        chart_type = chart.get("chart_type", "bar")
        time_freq = chart.get("time_freq", "M")

        if operation not in self.VALID_OPERATIONS:
            operation = "groupby"

        if chart_type not in self.VALID_CHART_TYPES or chart_type == "none":
            chart_type = "bar"

        if time_freq not in ["D", "M", "Y"]:
            time_freq = "M"

        aggregation = self._as_list(chart.get("aggregation", ["sum"]))

        aggregation = [
            agg for agg in aggregation
            if agg in self.VALID_AGGREGATIONS
        ]

        if not aggregation:
            aggregation = ["sum"]

        group_by_column = (
            self._first_existing(chart.get("group_by"), columns)
            or self._find_column(chart.get("x"), columns)
            or self._preferred_column(
                categorical_columns or columns,
                [
                    "campanha",
                    "canal",
                    "categoria",
                    "produto",
                    "região",
                    "regiao",
                    "status",
                    "cliente",
                ],
            )
        )

        metric_column = (
            self._first_existing(chart.get("metric"), columns)
            or self._find_column(chart.get("y"), columns)
            or self._preferred_column(
                numeric_columns,
                [
                    "receita",
                    "valor",
                    "valor total",
                    "roi",
                    "conversões",
                    "conversoes",
                    "vendas",
                    "quantidade",
                    "investimento",
                    "custo",
                ],
            )
        )

        time_column = (
            self._find_column(chart.get("time_column"), columns)
            or self._find_column(chart.get("date_column"), columns)
            or self._preferred_column(
                date_columns,
                ["data", "date", "dia", "mês", "mes", "ano"],
            )
        )

        if operation == "count":
            metric = []
            aggregation = ["count"]
            y = "count"
            x = group_by_column

        elif operation == "time_groupby":
            if not time_column:
                operation = "groupby"

            if operation == "time_groupby":
                if chart_type not in ["line", "area"]:
                    chart_type = "line"

                if aggregation == ["count"]:
                    metric = []
                    y = "count"
                else:
                    metric = [metric_column] if metric_column else []
                    y = metric_column

                x = time_column
                group_by_column = time_column

            else:
                metric = [metric_column] if metric_column else []
                x = group_by_column
                y = metric_column

        else:
            operation = "groupby"
            metric = [metric_column] if metric_column else []
            x = group_by_column
            y = metric_column

        if operation == "groupby":
            if not group_by_column:
                group_by_column = self._preferred_column(categorical_columns or columns, [])

            if not metric and aggregation != ["count"]:
                metric_column = self._preferred_column(numeric_columns, [])
                metric = [metric_column] if metric_column else []
                y = metric_column

            if not group_by_column:
                operation = "count"
                aggregation = ["count"]
                metric = []
                x = self._preferred_column(columns, [])
                y = "count"

        title = chart.get("title") or f"Gráfico {index + 1}"

        return {
            "title": title,
            "operation": operation,
            "group_by": [group_by_column] if group_by_column and operation != "time_groupby" else ([time_column] if time_column else []),
            "metric": metric,
            "aggregation": aggregation,
            "chart_type": chart_type,
            "x": x,
            "y": y,
            "time_column": time_column if operation == "time_groupby" else None,
            "time_freq": time_freq,
            "reason": chart.get("reason", ""),
        }

    def _safe_dashboard_plan(self, output_text: str, schema: dict) -> dict:
        columns = self._schema_columns(schema)
        numeric_columns = self._numeric_columns(schema, columns)
        categorical_columns = self._categorical_columns(schema, columns, numeric_columns)
        date_columns = self._date_columns(schema, columns)

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

            rename_columns = {
                original: friendly
                for original, friendly in rename_columns.items()
                if self._find_column(original, columns)
            }

            raw_charts = data.get("charts")

            if not isinstance(raw_charts, list):
                raw_charts = [data]

            charts = [
                self._normalize_chart_plan(
                    chart=chart,
                    index=index,
                    columns=columns,
                    numeric_columns=numeric_columns,
                    categorical_columns=categorical_columns,
                    date_columns=date_columns,
                )
                for index, chart in enumerate(raw_charts[:4])
                if isinstance(chart, dict)
            ]

            charts = [
                chart
                for chart in charts
                if chart.get("x") or chart.get("group_by") or chart.get("time_column")
            ]

            if not charts:
                fallback_x = self._preferred_column(categorical_columns or columns, [])
                fallback_metric = self._preferred_column(numeric_columns, [])

                if fallback_x and fallback_metric:
                    fallback_chart = {
                        "title": "Resumo por categoria",
                        "operation": "groupby",
                        "group_by": [fallback_x],
                        "metric": [fallback_metric],
                        "aggregation": ["sum"],
                        "chart_type": "bar",
                        "x": fallback_x,
                        "y": fallback_metric,
                        "time_column": None,
                        "time_freq": "M",
                        "reason": "fallback_com_colunas_disponiveis",
                    }
                else:
                    fallback_chart = {
                        "title": "Contagem de registros",
                        "operation": "count",
                        "group_by": [fallback_x] if fallback_x else [],
                        "metric": [],
                        "aggregation": ["count"],
                        "chart_type": "bar",
                        "x": fallback_x,
                        "y": "count",
                        "time_column": None,
                        "time_freq": "M",
                        "reason": "fallback_count",
                    }

                charts = [fallback_chart]

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
            fallback_x = self._preferred_column(categorical_columns or columns, [])
            fallback_metric = self._preferred_column(numeric_columns, [])

            if fallback_x and fallback_metric:
                fallback_chart = {
                    "title": "Resumo por categoria",
                    "operation": "groupby",
                    "group_by": [fallback_x],
                    "metric": [fallback_metric],
                    "aggregation": ["sum"],
                    "chart_type": "bar",
                    "x": fallback_x,
                    "y": fallback_metric,
                    "time_column": None,
                    "time_freq": "M",
                    "reason": "json_invalido_fallback_groupby",
                }
            else:
                fallback_chart = {
                    "title": "Contagem de registros",
                    "operation": "count",
                    "group_by": [fallback_x] if fallback_x else [],
                    "metric": [],
                    "aggregation": ["count"],
                    "chart_type": "bar",
                    "x": fallback_x,
                    "y": "count",
                    "time_column": None,
                    "time_freq": "M",
                    "reason": "json_invalido_fallback_count",
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

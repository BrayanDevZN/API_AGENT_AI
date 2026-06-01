import json
import unicodedata
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
        "kpi",
        "none",
    ]

    VALID_OPERATIONS = [
        "groupby",
        "count",
        "time_groupby",
        "scatter",
        "kpi",
        "table",
    ]

    VALID_AGGREGATIONS = [
        "sum",
        "mean",
        "count",
        "max",
        "min",
        "median",
        "none",
    ]

    VALID_TIME_FREQS = ["D", "W", "M", "Q", "Y"]

    MAX_CHARTS = 10

    METRIC_ALIASES = {
        "cliques": ["clique", "cliques", "click", "clicks"],
        "impressões": ["impressao", "impressoes", "impressão", "impressões", "impression", "impressions"],
        "conversões": ["conversao", "conversoes", "conversão", "conversões", "conversion", "conversions"],
        "receita": ["receita", "faturamento", "revenue", "valor total", "total receita"],
        "investimento": ["investimento", "gasto", "custo", "spend", "cost"],
        "vendas": ["venda", "vendas", "sales"],
        "quantidade": ["quantidade", "qtd", "volume", "quantity"],
        "pedidos": ["pedido", "pedidos", "orders"],
        "clientes": ["cliente", "clientes", "customers"],
    }

    def __init__(self):
        self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
        self.model = Settings.OPENAI_MODEL

    def run(self, question: str, columns: list[str], messages: list) -> dict:
        prompt = (
            self._analysis_prompt(question, columns, messages)
            if columns
            else self._chat_prompt(question, messages)
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        return self._safe_json(response.output_text, columns)

    def dashboard_plan(self, prompt: str, schema: dict) -> dict:
        system_prompt = """
Você é um planejador especialista em visualização de dados.

Sua função NÃO é escrever análise.
Sua função é escolher gráficos coerentes para outro agente analisar depois.

Responda SOMENTE em JSON válido.
Não use markdown.
Não explique fora do JSON.

FORMATO:
{
  "tool": "dashboard_plan",
  "dataset_type": "marketing | vendas | financeiro | ecommerce | rh | atendimento | produto | operacional | generico",
  "rename_columns": {
    "coluna_original": "Nome amigável"
  },
  "charts": [
    {
      "title": "Título claro e coerente",
      "operation": "groupby | count | time_groupby | scatter | kpi | table",
      "chart_type": "bar | horizontal_bar | line | area | pie | donut | scatter | table | kpi",
      "group_by": ["coluna_categorica"],
      "metric": ["coluna_numerica"],
      "aggregation": ["sum"],
      "x": "coluna_x_ou_null",
      "y": "coluna_y_ou_null",
      "time_column": "coluna_data_ou_null",
      "time_freq": "D | W | M | Q | Y",
      "limit": 10,
      "sort": "desc | asc | none",
      "reason": "motivo curto"
    }
  ]
}

REGRAS:
- Use apenas colunas existentes no schema.
- Nunca invente coluna.
- Não use métrica derivada se ela não existir.
- O título precisa combinar com metric, group_by e aggregation.
- Se o título falar cliques, use coluna de cliques.
- Se o título falar receita, use coluna de receita.
- Se o título falar conversões, use coluna de conversões.
- Se não existir a métrica citada no título, mude o título.
- Para count, metric deve ser [] e aggregation ["count"].
- Para kpi, chart_type deve ser "kpi".
- Para scatter, use duas colunas numéricas.
- Para time_groupby, use coluna temporal real.
- Não use pie/donut com mais de 6 categorias.
- Não use line sem data.
- Não use scatter com texto.
- Ranking deve usar horizontal_bar.
- Evolução temporal deve usar line ou area.
- Retorne entre 3 e 10 gráficos úteis.
- Se o dataset for simples, retorne menos.
- rename_columns é só visual. Os gráficos usam nomes originais.
"""

        user_prompt = f"""
Pedido do usuário:
{prompt if prompt and prompt.strip() else "Crie um dashboard visual útil para análise geral do dataset."}

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

        return self._safe_dashboard_plan(response.output_text, schema)

    def _chat_prompt(self, question: str, messages: list) -> str:
        return f"""
Responda SOMENTE JSON válido.

{{
  "chart_type": "none",
  "x": null,
  "y": null,
  "aggregation": "none",
  "mode": "chat",
  "reason": "sem_dataset",
  "rename_columns": {{}}
}}

Pergunta:
{question}

Histórico:
{json.dumps(messages, ensure_ascii=False)}
"""

    def _analysis_prompt(self, question: str, columns: list[str], messages: list) -> str:
        return f"""
Você interpreta pedidos de gráfico.

Responda SOMENTE JSON válido.

{{
  "chart_type": "bar | horizontal_bar | line | area | pie | donut | scatter | table | kpi | none",
  "x": "coluna_ou_null",
  "y": "coluna_ou_null",
  "aggregation": "sum | mean | count | max | min | median | none",
  "mode": "analysis | chat",
  "reason": "explicacao_curta",
  "rename_columns": {{
    "nome_original": "Nome Intuitivo"
  }}
}}

REGRAS:
- Use apenas colunas existentes.
- Não invente métricas.
- Para count, y deve ser null.
- Para sum/mean/max/min/median, y deve ser coluna real.
- Se for conversa comum, mode chat.

Pergunta:
{question}

Colunas:
{json.dumps(columns, ensure_ascii=False)}

Histórico:
{json.dumps(messages, ensure_ascii=False)}
"""

    def _as_list(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [item for item in value if item not in [None, ""]]
        return [value]

    def _normalize_name(self, value) -> str:
        text = str(value).strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        return text

    def _schema_columns(self, schema: dict) -> list[str]:
        columns = schema.get("columns") or schema.get("colunas") or []

        if isinstance(columns, dict):
            return list(columns.keys())

        result = []

        if isinstance(columns, list):
            for item in columns:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    name = item.get("name") or item.get("column") or item.get("nome")
                    if name:
                        result.append(name)

        return result

    def _numeric_columns(self, schema: dict, columns: list[str]) -> list[str]:
        for key in ["numeric_columns", "numerical_columns", "numeric", "numericas", "numéricas"]:
            values = schema.get(key)
            if isinstance(values, list):
                return [value for value in values if value in columns]

        typed_columns = schema.get("columns") or schema.get("colunas")

        result = []

        if isinstance(typed_columns, list):
            for item in typed_columns:
                if not isinstance(item, dict):
                    continue

                name = item.get("name") or item.get("column") or item.get("nome")
                dtype = self._normalize_name(item.get("type") or item.get("dtype") or "")

                if name in columns and any(term in dtype for term in [
                    "int",
                    "float",
                    "number",
                    "numeric",
                    "decimal",
                    "double",
                ]):
                    result.append(name)

        return result

    def _date_columns(self, schema: dict, columns: list[str]) -> list[str]:
        for key in ["date_columns", "datetime_columns", "data_columns", "datas"]:
            values = schema.get(key)
            if isinstance(values, list):
                return [value for value in values if value in columns]

        result = []

        for column in columns:
            name = self._normalize_name(column)
            if any(term in name for term in [
                "data",
                "date",
                "dia",
                "mes",
                "ano",
                "created",
                "updated",
                "timestamp",
            ]):
                result.append(column)

        return result

    def _categorical_columns(
        self,
        schema: dict,
        columns: list[str],
        numeric_columns: list[str],
        date_columns: list[str],
    ) -> list[str]:
        for key in ["categorical_columns", "categoricas", "categóricas", "categories"]:
            values = schema.get(key)
            if isinstance(values, list):
                return [value for value in values if value in columns]

        blocked = set(numeric_columns + date_columns)
        return [column for column in columns if column not in blocked]

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
        if not columns:
            return None

        preferred_names = [self._normalize_name(name) for name in preferred_names]

        for preferred in preferred_names:
            for column in columns:
                if self._normalize_name(column) == preferred:
                    return column

        for preferred in preferred_names:
            for column in columns:
                if preferred in self._normalize_name(column):
                    return column

        return columns[0]

    def _metric_from_title(self, title: str, numeric_columns: list[str]) -> str | None:
        normalized_title = self._normalize_name(title)

        if not normalized_title:
            return None

        for column in numeric_columns:
            column_name = self._normalize_name(column)

            if column_name in normalized_title:
                return column

        for column in numeric_columns:
            column_name = self._normalize_name(column)

            for aliases in self.METRIC_ALIASES.values():
                normalized_aliases = [self._normalize_name(alias) for alias in aliases]

                column_matches_alias = any(alias in column_name for alias in normalized_aliases)
                title_matches_alias = any(alias in normalized_title for alias in normalized_aliases)

                if column_matches_alias and title_matches_alias:
                    return column

        return None

    def _category_from_title(self, title: str, categorical_columns: list[str]) -> str | None:
        normalized_title = self._normalize_name(title)

        for column in categorical_columns:
            column_name = self._normalize_name(column)

            if column_name in normalized_title:
                return column

        return None

    def _clean_rename_columns(self, rename_columns: dict, columns: list[str]) -> dict:
        if not isinstance(rename_columns, dict):
            return {}

        result = {}

        for original, friendly in rename_columns.items():
            found = self._find_column(original, columns)

            if found and isinstance(friendly, str) and friendly.strip():
                result[found] = friendly.strip()

        return result

    def _safe_json(self, output_text: str, columns: list[str] | None = None) -> dict:
        columns = columns or []

        try:
            data = json.loads(output_text)
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

        chart_type = data.get("chart_type", "none")
        aggregation = data.get("aggregation", "none")
        mode = data.get("mode", "chat")

        if chart_type not in self.VALID_CHART_TYPES:
            chart_type = "none"

        if aggregation not in self.VALID_AGGREGATIONS:
            aggregation = "none"

        if mode not in ["analysis", "chat"]:
            mode = "chat"

        x = self._find_column(data.get("x"), columns)
        y = self._find_column(data.get("y"), columns)

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
            "reason": data.get("reason", ""),
            "rename_columns": self._clean_rename_columns(data.get("rename_columns", {}), columns),
        }

    def _normalize_chart_plan(
        self,
        chart: dict,
        index: int,
        columns: list[str],
        numeric_columns: list[str],
        categorical_columns: list[str],
        date_columns: list[str],
    ) -> dict | None:
        title = chart.get("title")

        if not isinstance(title, str) or not title.strip():
            title = f"Gráfico {index + 1}"

        title = title.strip()

        operation = chart.get("operation") or "groupby"
        chart_type = chart.get("chart_type") or "bar"

        if operation not in self.VALID_OPERATIONS:
            operation = "groupby"

        if chart_type not in self.VALID_CHART_TYPES or chart_type == "none":
            chart_type = "bar"

        aggregation = [
            agg for agg in self._as_list(chart.get("aggregation"))
            if agg in self.VALID_AGGREGATIONS
        ] or ["sum"]

        time_freq = chart.get("time_freq") or "M"

        if time_freq not in self.VALID_TIME_FREQS:
            time_freq = "M"

        group_by = self._first_existing(chart.get("group_by"), columns)
        metric = self._first_existing(chart.get("metric"), columns)
        x = self._find_column(chart.get("x"), columns)
        y = self._find_column(chart.get("y"), columns)
        time_column = self._find_column(chart.get("time_column"), columns)

        title_metric = self._metric_from_title(title, numeric_columns)
        title_category = self._category_from_title(title, categorical_columns)

        preferred_category = self._preferred_column(
            categorical_columns,
            [
                "campanha",
                "canal",
                "categoria",
                "produto",
                "cliente",
                "regiao",
                "região",
                "cidade",
                "status",
                "tipo",
                "departamento",
                "cargo",
            ],
        )

        preferred_metric = self._preferred_column(
            numeric_columns,
            [
                "receita",
                "valor",
                "total",
                "vendas",
                "quantidade",
                "pedidos",
                "cliques",
                "impressoes",
                "impressões",
                "conversoes",
                "conversões",
                "investimento",
                "custo",
                "preco",
                "preço",
                "salario",
                "salário",
            ],
        )

        preferred_date = self._preferred_column(
            date_columns,
            [
                "data",
                "date",
                "dia",
                "mes",
                "ano",
                "created_at",
                "timestamp",
            ],
        )

        if operation == "kpi":
            metric = title_metric or metric or y or preferred_metric

            if not metric:
                return None

            chart_type = "kpi"
            group_by_list = []
            metric_list = [metric]
            x = None
            y = metric
            time_column = None

            if aggregation == ["none"]:
                aggregation = ["sum"]

            title = self._coherent_title(title, operation, metric, None, aggregation[0])

        elif operation == "scatter":
            nums = []

            for col in [x, y, metric]:
                if col in numeric_columns and col not in nums:
                    nums.append(col)

            for col in numeric_columns:
                if col not in nums:
                    nums.append(col)

            if len(nums) < 2:
                return None

            chart_type = "scatter"
            x = nums[0]
            y = nums[1]
            metric_list = [y]
            group_by_list = []
            aggregation = ["none"]
            time_column = None
            title = f"Relação entre {x} e {y}"

        elif operation == "time_groupby":
            time_column = time_column or x or preferred_date

            if time_column not in date_columns:
                return None

            metric = title_metric or metric or y or preferred_metric

            if metric:
                metric_list = [metric]
                y = metric

                if aggregation == ["none"]:
                    aggregation = ["sum"]
            else:
                metric_list = []
                y = "count"
                aggregation = ["count"]

            x = time_column
            group_by_list = [time_column]

            if chart_type not in ["line", "area", "bar"]:
                chart_type = "line"

            title = self._coherent_title(title, operation, metric or "Registros", time_column, aggregation[0])

        elif operation == "count":
            group_by = title_category or group_by or x or preferred_category

            if not group_by:
                return None

            chart_type = chart_type if chart_type in ["bar", "horizontal_bar", "pie", "donut", "table"] else "bar"
            x = group_by
            y = "count"
            metric_list = []
            group_by_list = [group_by]
            aggregation = ["count"]
            time_column = None
            title = f"Quantidade por {group_by}"

        elif operation == "table":
            chart_type = "table"
            group_by = title_category or group_by or x or preferred_category
            metric = title_metric or metric or y or preferred_metric

            if not group_by and not metric:
                return None

            x = group_by
            y = metric
            group_by_list = [group_by] if group_by else []
            metric_list = [metric] if metric else []
            time_column = None

        else:
            operation = "groupby"
            group_by = title_category or group_by or x or preferred_category
            metric = title_metric or metric or y or preferred_metric

            if not group_by:
                return None

            if not metric:
                operation = "count"
                aggregation = ["count"]
                metric_list = []
                y = "count"
                title = f"Quantidade por {group_by}"
            else:
                metric_list = [metric]
                y = metric

                if aggregation in [["none"], ["count"]]:
                    aggregation = ["sum"]

                title = self._coherent_title(title, operation, metric, group_by, aggregation[0])

            x = group_by
            group_by_list = [group_by]
            time_column = None

            if chart_type not in ["bar", "horizontal_bar", "pie", "donut", "table"]:
                chart_type = "bar"

        limit = self._normalize_limit(chart.get("limit", 10), chart_type)
        sort = chart.get("sort", "desc")

        if sort not in ["desc", "asc", "none"]:
            sort = "desc"

        return {
            "title": title,
            "operation": operation,
            "group_by": group_by_list,
            "metric": metric_list,
            "aggregation": aggregation,
            "chart_type": chart_type,
            "x": x,
            "y": y,
            "time_column": time_column if operation == "time_groupby" else None,
            "time_freq": time_freq,
            "limit": limit,
            "sort": sort,
            "reason": chart.get("reason", ""),
        }

    def _coherent_title(self, title: str, operation: str, metric: str | None, group_or_time: str | None, aggregation: str) -> str:
        if not metric:
            return title

        agg_names = {
            "sum": "Total de",
            "mean": "Média de",
            "max": "Maior valor de",
            "min": "Menor valor de",
            "median": "Mediana de",
            "count": "Quantidade de",
            "none": "",
        }

        prefix = agg_names.get(aggregation, "Total de")

        if operation == "time_groupby" and group_or_time:
            return f"{prefix} {metric} ao longo do tempo"

        if operation == "groupby" and group_or_time:
            return f"{prefix} {metric} por {group_or_time}"

        if operation == "kpi":
            return f"{prefix} {metric}"

        return title

    def _normalize_limit(self, value, chart_type: str) -> int:
        try:
            limit = int(value)
        except Exception:
            limit = 10

        limit = max(1, min(limit, 20))

        if chart_type in ["pie", "donut"]:
            return min(limit, 6)

        if chart_type == "bar":
            return min(limit, 12)

        if chart_type == "horizontal_bar":
            return min(limit, 15)

        if chart_type == "kpi":
            return 1

        return limit

    def _fallback_charts(
        self,
        numeric_columns: list[str],
        categorical_columns: list[str],
        date_columns: list[str],
    ) -> list[dict]:
        charts = []

        main_metric = self._preferred_column(
            numeric_columns,
            ["receita", "valor", "total", "vendas", "quantidade", "cliques", "conversões", "conversoes"],
        )

        main_category = self._preferred_column(
            categorical_columns,
            ["categoria", "produto", "campanha", "canal", "cliente", "região", "regiao", "status"],
        )

        main_date = self._preferred_column(
            date_columns,
            ["data", "date", "dia", "mes", "ano"],
        )

        if main_metric:
            charts.append({
                "title": f"Total de {main_metric}",
                "operation": "kpi",
                "group_by": [],
                "metric": [main_metric],
                "aggregation": ["sum"],
                "chart_type": "kpi",
                "x": None,
                "y": main_metric,
                "time_column": None,
                "time_freq": "M",
                "limit": 1,
                "sort": "none",
                "reason": "Resumo da principal métrica numérica.",
            })

        if main_category and main_metric:
            charts.append({
                "title": f"Total de {main_metric} por {main_category}",
                "operation": "groupby",
                "group_by": [main_category],
                "metric": [main_metric],
                "aggregation": ["sum"],
                "chart_type": "horizontal_bar",
                "x": main_category,
                "y": main_metric,
                "time_column": None,
                "time_freq": "M",
                "limit": 10,
                "sort": "desc",
                "reason": "Ranking por categoria.",
            })

        if main_date and main_metric:
            charts.append({
                "title": f"Total de {main_metric} ao longo do tempo",
                "operation": "time_groupby",
                "group_by": [main_date],
                "metric": [main_metric],
                "aggregation": ["sum"],
                "chart_type": "line",
                "x": main_date,
                "y": main_metric,
                "time_column": main_date,
                "time_freq": "M",
                "limit": 12,
                "sort": "asc",
                "reason": "Tendência temporal.",
            })

        if len(numeric_columns) >= 2:
            charts.append({
                "title": f"Relação entre {numeric_columns[0]} e {numeric_columns[1]}",
                "operation": "scatter",
                "group_by": [],
                "metric": [numeric_columns[1]],
                "aggregation": ["none"],
                "chart_type": "scatter",
                "x": numeric_columns[0],
                "y": numeric_columns[1],
                "time_column": None,
                "time_freq": "M",
                "limit": 20,
                "sort": "none",
                "reason": "Relação entre duas variáveis numéricas.",
            })

        if main_category and not main_metric:
            charts.append({
                "title": f"Quantidade por {main_category}",
                "operation": "count",
                "group_by": [main_category],
                "metric": [],
                "aggregation": ["count"],
                "chart_type": "bar",
                "x": main_category,
                "y": "count",
                "time_column": None,
                "time_freq": "M",
                "limit": 10,
                "sort": "desc",
                "reason": "Contagem por categoria.",
            })

        return charts

    def _safe_dashboard_plan(self, output_text: str, schema: dict) -> dict:
        columns = self._schema_columns(schema)
        numeric_columns = self._numeric_columns(schema, columns)
        date_columns = self._date_columns(schema, columns)
        categorical_columns = self._categorical_columns(schema, columns, numeric_columns, date_columns)

        try:
            data = json.loads(output_text)
        except Exception:
            data = {}

        raw_charts = data.get("charts", [])

        if isinstance(raw_charts, dict):
            raw_charts = [raw_charts]

        if not isinstance(raw_charts, list):
            raw_charts = []

        charts = []

        for index, raw_chart in enumerate(raw_charts[:self.MAX_CHARTS]):
            if not isinstance(raw_chart, dict):
                continue

            normalized = self._normalize_chart_plan(
                chart=raw_chart,
                index=index,
                columns=columns,
                numeric_columns=numeric_columns,
                categorical_columns=categorical_columns,
                date_columns=date_columns,
            )

            if normalized:
                charts.append(normalized)

        if not charts:
            charts = self._fallback_charts(
                numeric_columns=numeric_columns,
                categorical_columns=categorical_columns,
                date_columns=date_columns,
            )

        if not charts:
            fallback_x = columns[0] if columns else None
            charts = [{
                "title": "Tabela de dados",
                "operation": "table",
                "group_by": [fallback_x] if fallback_x else [],
                "metric": [],
                "aggregation": ["none"],
                "chart_type": "table",
                "x": fallback_x,
                "y": None,
                "time_column": None,
                "time_freq": "M",
                "limit": 20,
                "sort": "none",
                "reason": "Não havia colunas suficientes para gráfico útil.",
            }]

        first_chart = charts[0]

        return {
            "tool": "dashboard_plan",
            "dataset_type": data.get("dataset_type", "generico"),
            "rename_columns": self._clean_rename_columns(data.get("rename_columns", {}), columns),
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
            "limit": first_chart["limit"],
            "sort": first_chart["sort"],
        }
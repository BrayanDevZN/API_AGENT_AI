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

    def __init__(self):
        self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
        self.model = Settings.OPENAI_MODEL

    def run(self, question: str, columns: list[str], messages: list) -> dict:
        if not columns:
            prompt = self._chat_prompt(question, messages)
        else:
            prompt = self._analysis_prompt(question, columns, messages)

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        return self._safe_json(response.output_text, columns)

    def dashboard_plan(self, prompt: str, schema: dict) -> dict:
        system_prompt = """
Você é um planejador especialista em visualização de dados.

Sua função NÃO é escrever análise.
Sua função é escolher os melhores gráficos para que outro agente consiga analisar o dataset depois.

Você deve pensar como um analista de BI:
1. entender o tipo de dataset;
2. identificar colunas categóricas, numéricas e temporais;
3. escolher gráficos úteis;
4. evitar gráficos ruins;
5. criar um plano visual claro.

Responda SOMENTE em JSON válido.
Não use markdown.
Não explique fora do JSON.

FORMATO OBRIGATÓRIO:
{
  "tool": "dashboard_plan",
  "dataset_type": "marketing | vendas | financeiro | ecommerce | rh | atendimento | produto | operacional | generico",
  "rename_columns": {
    "coluna_original": "Nome amigável"
  },
  "charts": [
    {
      "title": "Título claro do gráfico",
      "operation": "groupby | count | time_groupby | scatter | kpi | table",
      "chart_type": "bar | horizontal_bar | line | area | pie | donut | scatter | table | kpi",
      "group_by": ["coluna_categorica"],
      "metric": ["coluna_numerica"],
      "aggregation": ["sum"],
      "x": "coluna_eixo_x_ou_null",
      "y": "coluna_eixo_y_ou_null",
      "time_column": "coluna_data_ou_null",
      "time_freq": "D | W | M | Q | Y",
      "limit": 10,
      "sort": "desc | asc | none",
      "reason": "motivo curto da escolha"
    }
  ]
}

REGRAS ABSOLUTAS:
- Use apenas colunas existentes no schema.
- Nunca invente coluna.
- Nunca use coluna derivada que não exista.
- Não crie ROI, lucro, margem, ticket médio, CTR ou taxa de conversão se essas colunas não existirem.
- Se quiser sugerir métrica derivada, coloque apenas em reason, mas NÃO use como metric.
- group_by sempre deve ser lista.
- metric sempre deve ser lista.
- aggregation sempre deve ser lista.
- Para count, metric deve ser [] e aggregation deve ser ["count"].
- Para kpi, chart_type deve ser "kpi".
- Para scatter, precisa de 2 colunas numéricas reais.
- Para time_groupby, precisa de coluna temporal real.
- Retorne entre 3 e 10 gráficos quando o dataset permitir.
- Se o dataset for muito simples, retorne menos gráficos.
- Se não houver coluna numérica, priorize count e table.
- Se não houver coluna temporal, não use line nem area por tempo.
- O objetivo é gerar gráficos úteis, não muitos gráficos inúteis.

REGRAS DE ESCOLHA DE GRÁFICO:
- bar: comparação entre poucas/médias categorias.
- horizontal_bar: ranking, top N, nomes longos ou muitas categorias.
- line: evolução temporal de uma métrica.
- area: evolução temporal de volume ou tendência acumulada.
- pie: participação percentual com no máximo 6 categorias.
- donut: igual pie, só quando fizer sentido visual.
- scatter: relação entre duas métricas numéricas.
- table: quando há muitas categorias ou quando gráfico ficaria confuso.
- kpi: valor único importante, como soma, média, máximo, mínimo ou contagem.

REGRAS PARA EVITAR GRÁFICOS RUINS:
- Não use pie/donut com muitas categorias.
- Não use line sem coluna de data.
- Não use scatter com coluna categórica.
- Não use bar com mais de 15 categorias sem limit.
- Para ranking, use horizontal_bar com limit entre 5 e 15.
- Para distribuição temporal, use line ou area.
- Para composição percentual, use pie/donut apenas com poucas categorias.
- Para dataset desconhecido, monte visão geral: KPIs, ranking, comparação por categoria e evolução temporal se houver data.

ESTRATÉGIA PARA DATASETS COMUNS:

MARKETING:
- KPIs: soma de impressões, cliques, conversões, receita, investimento se existirem.
- Gráficos úteis: evolução temporal, ranking por campanha, comparação por canal, relação investimento x receita.
- Evite pizza por data.

VENDAS / ECOMMERCE:
- KPIs: receita, quantidade, pedidos, clientes.
- Gráficos úteis: receita por produto/categoria, vendas por região, evolução por mês, top produtos/clientes.

FINANCEIRO:
- KPIs: receita, custo, despesa, lucro se existir.
- Gráficos úteis: evolução mensal, gastos por categoria, receitas por fonte, ranking de maiores valores.

RH:
- KPIs: funcionários, salário médio, admissões, desligamentos se existirem.
- Gráficos úteis: funcionários por área, salário por cargo, evolução de admissões.

ATENDIMENTO:
- KPIs: tickets, tempo médio, satisfação, resolvidos.
- Gráficos úteis: chamados por status, canal, prioridade, evolução temporal.

REGRAS PARA rename_columns:
- Sempre retorne rename_columns.
- Chaves devem ser exatamente colunas existentes.
- Valores devem ser nomes amigáveis.
- Os gráficos devem usar os nomes originais, nunca os nomes amigáveis.
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
Você é um interpretador de intenção.

Não existe dataset disponível.
Então responda como conversa normal.

Responda SOMENTE em JSON válido.

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
Você é um interpretador de intenção para análise de dados.

Responda SOMENTE em JSON válido.

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
- Se for conversa comum, use mode chat.
- Se for pedido sobre dados, use mode analysis.
- Para count, y deve ser null.
- Para gráfico, x deve ser coluna real.
- Para sum/mean/max/min/median, y deve ser coluna real.

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
        for key in ["numeric_columns", "numerical_columns", "numeric", "numericas", "numéricas"]:
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

        return []

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
                "mês",
                "ano",
                "created",
                "updated",
                "timestamp",
            ]):
                result.append(column)

        return result

    def _categorical_columns(self, schema: dict, columns: list[str], numeric_columns: list[str], date_columns: list[str]) -> list[str]:
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

        for preferred in preferred_names:
            for column in columns:
                if self._normalize_name(column) == preferred:
                    return column

        for preferred in preferred_names:
            for column in columns:
                if preferred in self._normalize_name(column):
                    return column

        return columns[0]

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
        operation = chart.get("operation") or "groupby"
        chart_type = chart.get("chart_type") or "bar"

        if operation not in self.VALID_OPERATIONS:
            operation = "groupby"

        if chart_type not in self.VALID_CHART_TYPES or chart_type == "none":
            chart_type = "bar"

        aggregation = [
            agg for agg in self._as_list(chart.get("aggregation"))
            if agg in self.VALID_AGGREGATIONS
        ]

        if not aggregation:
            aggregation = ["sum"]

        time_freq = chart.get("time_freq") or "M"

        if time_freq not in self.VALID_TIME_FREQS:
            time_freq = "M"

        group_by = self._first_existing(chart.get("group_by"), columns)
        metric = self._first_existing(chart.get("metric"), columns)
        x = self._find_column(chart.get("x"), columns)
        y = self._find_column(chart.get("y"), columns)
        time_column = self._find_column(chart.get("time_column"), columns)

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
                "mês",
                "ano",
                "created_at",
                "timestamp",
            ],
        )

        if operation == "kpi":
            metric = metric or y or preferred_metric

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

        elif operation == "time_groupby":
            time_column = time_column or x or preferred_date

            if time_column not in date_columns:
                return None

            metric = metric or y or preferred_metric

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

        elif operation == "count":
            group_by = group_by or x or preferred_category

            if not group_by:
                return None

            chart_type = chart_type if chart_type in ["bar", "horizontal_bar", "pie", "donut", "table"] else "bar"
            x = group_by
            y = "count"
            metric_list = []
            group_by_list = [group_by]
            aggregation = ["count"]
            time_column = None

        elif operation == "table":
            chart_type = "table"
            group_by = group_by or x or preferred_category
            metric = metric or y or preferred_metric

            if not group_by and not metric:
                return None

            x = group_by
            y = metric
            group_by_list = [group_by] if group_by else []
            metric_list = [metric] if metric else []
            time_column = None

        else:
            operation = "groupby"
            group_by = group_by or x or preferred_category
            metric = metric or y or preferred_metric

            if not group_by:
                return None

            if not metric:
                operation = "count"
                aggregation = ["count"]
                metric_list = []
                y = "count"
            else:
                metric_list = [metric]
                y = metric

                if aggregation == ["none"] or aggregation == ["count"]:
                    aggregation = ["sum"]

            x = group_by
            group_by_list = [group_by]
            time_column = None

            if chart_type not in ["bar", "horizontal_bar", "pie", "donut", "table"]:
                chart_type = "bar"

        limit = chart.get("limit", 10)

        try:
            limit = int(limit)
        except Exception:
            limit = 10

        if limit < 3:
            limit = 3

        if limit > 20:
            limit = 20

        sort = chart.get("sort", "desc")

        if sort not in ["desc", "asc", "none"]:
            sort = "desc"

        if chart_type in ["pie", "donut"]:
            limit = min(limit, 6)

        if chart_type == "bar":
            limit = min(limit, 12)

        if chart_type == "horizontal_bar":
            limit = min(limit, 15)

        title = chart.get("title")

        if not isinstance(title, str) or not title.strip():
            title = f"Gráfico {index + 1}"

        return {
            "title": title.strip(),
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

    def _fallback_charts(
        self,
        numeric_columns: list[str],
        categorical_columns: list[str],
        date_columns: list[str],
    ) -> list[dict]:
        charts = []

        main_metric = self._preferred_column(numeric_columns, [
            "receita",
            "valor",
            "total",
            "vendas",
            "quantidade",
            "cliques",
            "conversões",
            "conversoes",
        ])

        main_category = self._preferred_column(categorical_columns, [
            "categoria",
            "produto",
            "campanha",
            "canal",
            "cliente",
            "região",
            "regiao",
            "status",
        ])

        main_date = self._preferred_column(date_columns, [
            "data",
            "date",
            "dia",
            "mês",
            "mes",
            "ano",
        ])

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
                "reason": "KPI geral para resumir a principal métrica numérica.",
            })

        if main_category and main_metric:
            charts.append({
                "title": f"{main_metric} por {main_category}",
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
                "reason": "Ranking das principais categorias por métrica.",
            })

        if main_date and main_metric:
            charts.append({
                "title": f"Evolução de {main_metric} ao longo do tempo",
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
                "reason": "Tendência temporal da principal métrica.",
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
                "reason": "Contagem por categoria disponível.",
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

        tool = data.get("tool", "dashboard_plan")

        if tool not in ["dashboard_plan", "chart_plan"]:
            tool = "dashboard_plan"

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
                "reason": "Não havia colunas suficientes para um gráfico estatístico útil.",
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
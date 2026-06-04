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

    DOMAIN_PRIORITY_METRICS = {
        "marketing": [
            "receita",
            "conversões",
            "conversoes",
            "cliques",
            "impressões",
            "impressoes",
            "investimento",
            "custo",
            "roi",
            "ctr",
            "cpc",
            "cpa",
        ],
        "vendas": [
            "receita",
            "vendas",
            "lucro",
            "ticket",
            "quantidade",
            "pedidos",
            "clientes",
            "valor",
        ],
        "financeiro": [
            "receita",
            "lucro",
            "despesa",
            "custo",
            "margem",
            "saldo",
            "valor",
            "total",
        ],
        "ecommerce": [
            "receita",
            "vendas",
            "pedidos",
            "ticket",
            "produto",
            "quantidade",
            "clientes",
            "frete",
        ],
        "rh": [
            "salário",
            "salario",
            "funcionários",
            "funcionarios",
            "departamento",
            "cargo",
            "idade",
            "turnover",
        ],
        "atendimento": [
            "chamados",
            "tickets",
            "tempo",
            "satisfação",
            "satisfacao",
            "status",
            "resolução",
            "resolucao",
        ],
        "produto": [
            "produto",
            "uso",
            "usuários",
            "usuarios",
            "retenção",
            "retencao",
            "churn",
            "feature",
        ],
        "operacional": [
            "quantidade",
            "tempo",
            "custo",
            "status",
            "produção",
            "producao",
            "entrega",
            "estoque",
        ],
        "generico": [
            "receita",
            "valor",
            "total",
            "quantidade",
            "vendas",
            "clientes",
            "pedidos",
        ],
    }

    def __init__(self):
        self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
        self.model = Settings.OPENAI_MODEL

    def run(self, question: str, columns: list[str], messages: list, unique_values: dict | None = None) -> dict:
        prompt = (
            self._analysis_prompt(question, columns, messages, unique_values or {})
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
  "analysis_type": "general | specific",
  "business_context": "contexto curto do dataset",
  "priority_metrics": ["métricas mais importantes encontradas no schema"],
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
      "drill_down_hierarchy": ["coluna_nivel_1", "coluna_nivel_2", "coluna_nivel_3"],
      "filters": [
        {
          "column": "coluna_existente",
          "operator": "equals | not_equals | contains | in",
          "value": "valor_exato_ou_lista_de_valores"
        }
      ],
      "limit": 10,
      "sort": "desc | asc | none",
      "reason": "motivo curto"
    }
  ]
}

REGRAS:
- Use filters quando o pedido limitar a analise a um subconjunto, como Status = APROVADO.
- Antes de criar filters, consulte schema.unique_values para usar exatamente o valor real da coluna, preservando maiusculas, minusculas, acentos e espacos.
- Se o usuario pedir "aprovado" e schema.unique_values mostrar "APROVADO", use value "APROVADO".
- Se nao houver valor correspondente em schema.unique_values, nao invente filtro.
- Use bar para comparar poucas categorias lado a lado.
- Use horizontal_bar para rankings, nomes longos ou muitas categorias.
- Use line para evolucao temporal com datas ordenadas.
- Use area para evolucao temporal acumulada ou volume ao longo do tempo.
- Use scatter somente para relacao entre duas colunas numericas.
- Use kpi para um unico numero importante.
- Use table quando o usuario pedir detalhes, listagem ou dados brutos.
- Use pie/donut apenas para composicao percentual com poucas categorias, idealmente entre 2 e 6 valores.
- Use drill_down_hierarchy quando houver colunas hierarquicas compativeis.
- Hierarquias recomendadas: Localizacao Regiao > Estado > Cidade; Tempo Ano > Trimestre > Mes > Dia; Produtos Categoria > Produto.
- drill_down_hierarchy deve conter apenas colunas reais do schema, na ordem do nivel mais amplo para o mais detalhado.
- Se a hierarquia depender de uma coluna de data unica, use time_column e deixe drill_down_hierarchy vazio.
- Use apenas colunas existentes no schema.
- Nunca invente coluna.
- Não use métrica derivada se ela não existir.
- O título precisa combinar com metric, group_by e aggregation.
- Se o título falar cliques, use coluna de cliques.
- Se o título falar receita, use coluna de receita.
- Se o título falar conversões, use coluna de conversões.
- Se não existir a métrica citada no título, mude o título.
- Para count, metric deve ser [] e aggregation ["count"].
- Para count, use y como "Quantidade", pois esta é a métrica agregada final exibida no gráfico.
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
- analysis_type deve ser "general" quando o pedido for amplo ou vazio.
- analysis_type deve ser "specific" quando o usuário pedir algo específico.
- business_context deve explicar em poucas palavras o provável contexto dos dados.
- priority_metrics deve conter apenas colunas reais do schema que sejam métricas importantes para o tipo de dataset.
- Para marketing, priorize métricas como receita, conversões, cliques, impressões, investimento, ROI, CTR, CPC e CPA se existirem.
- Para vendas/ecommerce, priorize receita, vendas, lucro, ticket, pedidos, quantidade, clientes e produtos se existirem.
- Para financeiro, priorize receita, despesa, lucro, custo, margem, saldo e valor se existirem.
- Para RH, priorize salário, funcionários, idade, cargo, departamento e turnover se existirem.
- Para atendimento, priorize chamados, tickets, tempo, satisfação, status e resolução se existirem.
- Nunca use a mesma coluna para x e y.
- Nunca use a mesma coluna em group_by e metric.
- Para groupby, group_by deve ser coluna categórica e metric deve ser coluna numérica.
- Se uma coluna numérica aparecer como group_by e também como metric, corrija usando uma coluna categórica para group_by.
- Exemplo errado: group_by ["Nota_Entrevista"] e metric ["Nota_Entrevista"].
- Exemplo certo: group_by ["Departamento"] e metric ["Nota_Entrevista"] com aggregation ["mean"].
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

    def _analysis_prompt(self, question: str, columns: list[str], messages: list, unique_values: dict | None = None) -> str:
        unique_values = unique_values or {}

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
  "filters": [
    {
      "column": "coluna_existente",
      "operator": "equals | not_equals | contains | in",
      "value": "valor_exato_ou_lista_de_valores"
    }
  ],
  "rename_columns": {{
    "nome_original": "Nome Intuitivo"
  }}
}}

REGRAS:
- Use apenas colunas existentes.
- Não invente métricas.
- Para count, y deve ser "Quantidade" quando for usado em dashboard ou null quando for apenas interpretação simples.
- Para sum/mean/max/min/median, y deve ser coluna real.
- Use filters quando o usuario pedir a analise somente para um subconjunto de linhas.
- Antes de criar filters, consulte Valores unicos para usar exatamente o valor real da coluna.
- Se o usuario pedir "aprovado" e Valores unicos mostrar "APROVADO", use value "APROVADO".
- Se for conversa comum, mode chat.

Pergunta:
{question}

Colunas:
{json.dumps(columns, ensure_ascii=False)}

Valores unicos:
{json.dumps(unique_values, ensure_ascii=False)}

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

    def _guess_dataset_type(self, schema: dict, columns: list[str]) -> str:
        schema_text = self._normalize_name(
            " ".join(columns) + " " + json.dumps(schema, ensure_ascii=False)
        )

        domain_scores = {
            "marketing": [
                "campanha",
                "canal",
                "clique",
                "click",
                "impress",
                "convers",
                "ctr",
                "cpc",
                "cpa",
                "roi",
                "leads",
                "ads",
                "anuncio",
                "anúncio",
                "investimento",
            ],
            "vendas": [
                "venda",
                "receita",
                "cliente",
                "pedido",
                "produto",
                "ticket",
                "faturamento",
                "lucro",
                "valor",
                "vendedor",
            ],
            "financeiro": [
                "despesa",
                "receita",
                "lucro",
                "custo",
                "margem",
                "saldo",
                "conta",
                "pagamento",
                "financeiro",
            ],
            "ecommerce": [
                "produto",
                "pedido",
                "frete",
                "carrinho",
                "categoria",
                "sku",
                "checkout",
                "cliente",
                "compra",
            ],
            "rh": [
                "funcionario",
                "funcionarios",
                "colaborador",
                "cargo",
                "departamento",
                "salario",
                "turnover",
                "idade",
                "admissao",
            ],
            "atendimento": [
                "chamado",
                "ticket",
                "atendimento",
                "suporte",
                "satisfacao",
                "satisfação",
                "sla",
                "resolucao",
                "resolução",
            ],
            "produto": [
                "feature",
                "uso",
                "usuario",
                "usuarios",
                "retencao",
                "retenção",
                "churn",
                "sessao",
                "evento",
            ],
            "operacional": [
                "estoque",
                "entrega",
                "producao",
                "produção",
                "operacao",
                "operação",
                "tempo",
                "status",
                "logistica",
                "logística",
            ],
        }

        best_domain = "generico"
        best_score = 0

        for domain, terms in domain_scores.items():
            score = sum(1 for term in terms if self._normalize_name(term) in schema_text)

            if score > best_score:
                best_score = score
                best_domain = domain

        return best_domain

    def _priority_metrics_for_domain(
        self,
        dataset_type: str,
        columns: list[str],
        numeric_columns: list[str],
    ) -> list[str]:
        priorities = self.DOMAIN_PRIORITY_METRICS.get(
            dataset_type,
            self.DOMAIN_PRIORITY_METRICS["generico"],
        )

        result = []

        for priority in priorities:
            normalized_priority = self._normalize_name(priority)

            for column in numeric_columns:
                normalized_column = self._normalize_name(column)

                if (
                    normalized_priority == normalized_column
                    or normalized_priority in normalized_column
                    or normalized_column in normalized_priority
                ):
                    if column not in result:
                        result.append(column)

        if not result:
            result = numeric_columns[:5]

        return result[:8]

    def _normalize_analysis_type(self, value, user_prompt: str | None) -> str:
        if value in ["general", "specific"]:
            return value

        if user_prompt and str(user_prompt).strip():
            return "specific"

        return "general"

    def _normalize_business_context(self, value, dataset_type: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()

        contexts = {
            "marketing": "Dados relacionados a campanhas, canais, investimento e desempenho de marketing.",
            "vendas": "Dados relacionados a vendas, clientes, produtos, pedidos e receita.",
            "financeiro": "Dados relacionados a valores financeiros, custos, receitas, despesas e resultados.",
            "ecommerce": "Dados relacionados a vendas online, produtos, pedidos, clientes e categorias.",
            "rh": "Dados relacionados a pessoas, cargos, departamentos, salários ou colaboradores.",
            "atendimento": "Dados relacionados a chamados, tickets, suporte, status e atendimento.",
            "produto": "Dados relacionados a uso de produto, usuários, funcionalidades e comportamento.",
            "operacional": "Dados relacionados a processos, estoque, entregas, produção ou operação.",
            "generico": "Dataset genérico com métricas e categorias para análise exploratória.",
        }

        return contexts.get(dataset_type, contexts["generico"])


    def _preferred_group_column_for_metric(
        self,
        metric: str | None,
        categorical_columns: list[str],
    ) -> str | None:
        preferred_names = [
            "departamento",
            "status",
            "vaga",
            "recrutador",
            "etapa_atual",
            "etapa atual",
            "regiao",
            "região",
            "cidade",
            "categoria",
            "produto",
            "canal",
            "campanha",
            "cliente",
            "tipo",
            "cargo",
        ]

        candidates = [
            column for column in categorical_columns
            if column != metric
        ]

        return self._preferred_column(candidates, preferred_names)

    def _preferred_metric_column_for_group(
        self,
        group_by: str | None,
        numeric_columns: list[str],
    ) -> str | None:
        preferred_names = [
            "receita",
            "valor",
            "total",
            "nota",
            "nota_entrevista",
            "nota entrevista",
            "salario",
            "salário",
            "quantidade",
            "lucro",
            "vendas",
            "pedidos",
            "cliques",
            "conversões",
            "conversoes",
            "investimento",
            "custo",
        ]

        candidates = [
            column for column in numeric_columns
            if column != group_by
        ]

        return self._preferred_column(candidates, preferred_names)

    def _fix_same_group_metric(
        self,
        group_by: str | None,
        metric: str | None,
        x: str | None,
        y: str | None,
        numeric_columns: list[str],
        categorical_columns: list[str],
    ) -> tuple[str | None, str | None, str | None, str | None]:
        if group_by and metric and group_by == metric:
            if group_by in numeric_columns:
                better_group = self._preferred_group_column_for_metric(
                    metric=metric,
                    categorical_columns=categorical_columns,
                )

                if better_group:
                    group_by = better_group
                    x = better_group
            else:
                better_metric = self._preferred_metric_column_for_group(
                    group_by=group_by,
                    numeric_columns=numeric_columns,
                )

                if better_metric:
                    metric = better_metric
                    y = better_metric

        if x and y and x == y:
            if x in numeric_columns:
                better_x = self._preferred_group_column_for_metric(
                    metric=y,
                    categorical_columns=categorical_columns,
                )

                if better_x:
                    x = better_x
                    group_by = better_x
            else:
                better_y = self._preferred_metric_column_for_group(
                    group_by=x,
                    numeric_columns=numeric_columns,
                )

                if better_y:
                    y = better_y
                    metric = better_y

        return group_by, metric, x, y


    def _clean_rename_columns(self, rename_columns: dict, columns: list[str]) -> dict:
        if not isinstance(rename_columns, dict):
            return {}

        result = {}

        for original, friendly in rename_columns.items():
            found = self._find_column(original, columns)

            if found and isinstance(friendly, str) and friendly.strip():
                result[found] = friendly.strip()

        return result

    def _normalize_filters(self, filters, columns: list[str]) -> list[dict]:
        if isinstance(filters, dict):
            filters = [filters]

        if not isinstance(filters, list):
            return []

        result = []
        valid_operators = {"equals", "not_equals", "contains", "in"}

        for filter_spec in filters:
            if not isinstance(filter_spec, dict):
                continue

            column = self._find_column(filter_spec.get("column"), columns)

            if not column:
                continue

            operator = str(filter_spec.get("operator") or "equals").strip().lower()

            if operator not in valid_operators:
                operator = "equals"

            value = filter_spec.get("value")

            if value is None:
                continue

            if isinstance(value, list):
                clean_value = [
                    str(item).strip()
                    for item in value
                    if item is not None and str(item).strip()
                ]

                if not clean_value:
                    continue
            else:
                clean_value = str(value).strip()

                if not clean_value:
                    continue

            result.append({
                "column": column,
                "operator": operator,
                "value": clean_value,
            })

        return result

    def _normalize_drill_down_hierarchy(self, hierarchy, columns: list[str]) -> list[str]:
        resolved = []

        for column in self._as_list(hierarchy):
            found = self._find_column(column, columns)

            if found and found not in resolved:
                resolved.append(found)

        return resolved if len(resolved) >= 2 else []

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
            "filters": self._normalize_filters(data.get("filters"), columns),
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

        group_by, metric, x, y = self._fix_same_group_metric(
            group_by=group_by,
            metric=metric,
            x=x,
            y=y,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
        )

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
                y = "Quantidade"
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
            y = "Quantidade"
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
                y = "Quantidade"
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

        if operation == "groupby":
            final_group = group_by_list[0] if group_by_list else None
            final_metric = metric_list[0] if metric_list else None

            if final_group and final_metric and final_group == final_metric:
                fixed_group, fixed_metric, fixed_x, fixed_y = self._fix_same_group_metric(
                    group_by=final_group,
                    metric=final_metric,
                    x=x,
                    y=y,
                    numeric_columns=numeric_columns,
                    categorical_columns=categorical_columns,
                )

                if fixed_group and fixed_metric and fixed_group != fixed_metric:
                    group_by_list = [fixed_group]
                    metric_list = [fixed_metric]
                    x = fixed_x or fixed_group
                    y = fixed_y or fixed_metric
                    title = self._coherent_title(
                        title,
                        operation,
                        fixed_metric,
                        fixed_group,
                        aggregation[0],
                    )
                else:
                    return None

        if x and y and x == y and operation not in ["scatter", "kpi"]:
            return None

        normalized_chart = {
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
            "drill_down_hierarchy": self._normalize_drill_down_hierarchy(
                chart.get("drill_down_hierarchy"),
                columns,
            ),
            "filters": self._normalize_filters(chart.get("filters"), columns),
            "limit": limit,
            "sort": sort,
            "reason": chart.get("reason", ""),
        }

        return self._fix_count_output_contract(normalized_chart)

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

    def _fix_count_output_contract(self, chart: dict) -> dict:
        """
        Em gráficos de contagem, o dado agregado final deve usar a mesma chave
        que o frontend vai procurar no chart_data.

        O pandas/analyzer normalmente gera algo como:
        {"Região": "Sudeste", "Quantidade": 120}

        Então chart_config.y não pode ser "count", porque essa chave não existe
        no chart_data final. O contrato correto é y = "Quantidade".
        """
        if not isinstance(chart, dict):
            return chart

        operation = chart.get("operation")
        aggregations = self._as_list(chart.get("aggregation"))
        y = chart.get("y")

        is_count_chart = (
            operation == "count"
            or "count" in aggregations
            or self._normalize_name(y) == "count"
        )

        if is_count_chart:
            chart["operation"] = "count" if operation != "time_groupby" else operation
            chart["metric"] = [] if operation != "time_groupby" else chart.get("metric", [])
            chart["aggregation"] = ["count"]
            chart["y"] = "Quantidade"

            if not chart.get("title") and chart.get("x"):
                chart["title"] = f"Quantidade por {chart['x']}"

        return chart


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
                "y": "Quantidade",
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

        inferred_dataset_type = self._guess_dataset_type(schema, columns)
        dataset_type = data.get("dataset_type") or inferred_dataset_type

        if dataset_type not in self.DOMAIN_PRIORITY_METRICS:
            dataset_type = inferred_dataset_type

        priority_metrics = [
            metric for metric in self._as_list(data.get("priority_metrics"))
            if self._find_column(metric, numeric_columns)
        ]

        priority_metrics = [
            self._find_column(metric, numeric_columns)
            for metric in priority_metrics
        ]

        priority_metrics = [
            metric for metric in priority_metrics
            if metric
        ]

        if not priority_metrics:
            priority_metrics = self._priority_metrics_for_domain(
                dataset_type=dataset_type,
                columns=columns,
                numeric_columns=numeric_columns,
            )

        analysis_type = self._normalize_analysis_type(
            data.get("analysis_type"),
            schema.get("user_prompt") or schema.get("prompt"),
        )

        business_context = self._normalize_business_context(
            data.get("business_context"),
            dataset_type,
        )

        return {
            "tool": "dashboard_plan",
            "dataset_type": dataset_type,
            "analysis_type": analysis_type,
            "business_context": business_context,
            "priority_metrics": priority_metrics,
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
            "drill_down_hierarchy": first_chart.get("drill_down_hierarchy", []),
            "filters": first_chart.get("filters", []),
            "limit": first_chart["limit"],
            "sort": first_chart["sort"],
        }

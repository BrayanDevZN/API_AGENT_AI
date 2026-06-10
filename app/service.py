import json
import unicodedata
from datetime import date, datetime

import pandas as pd

from app.accounts_client import AccountsClient
from app.interpreter import Interpreter
from app.analyzer import Analyzer
from app.generator import Generator
from app.data_cleaner import DataCleaner
from app.data_profiler import DataProfiler
from app.pandas_tools import PandasTools


AI_PAYLOAD_MAX_CHARS = 700_000
AI_UNIQUE_VALUES_LIMIT = 8
AI_COMPACT_UNIQUE_VALUES_LIMIT = 3
AI_CHART_DATA_LIMIT = 40
AI_COMPACT_CHART_DATA_LIMIT = 12


class Service:
    def __init__(self):
        self.accounts = AccountsClient()
        self.interpreter = Interpreter()
        self.analyzer = Analyzer()
        self.generator = Generator()
        self.cleaner = DataCleaner()
        self.profiler = DataProfiler()
        self.pandas_tools = PandasTools()

    def _normalize_prompt(self, prompt: str | None) -> str | None:
        if not prompt:
            return None

        prompt = str(prompt).strip()

        if not prompt:
            return None

        return prompt

    def _make_json_safe(self, value):
        if isinstance(value, dict):
            return {
                str(key): self._make_json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [self._make_json_safe(item) for item in value]

        if isinstance(value, tuple):
            return [self._make_json_safe(item) for item in value]

        if isinstance(value, pd.Timestamp):
            return value.isoformat()

        if isinstance(value, pd.Period):
            return str(value)

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if not isinstance(value, (list, dict, tuple, str)):
            try:
                if pd.isna(value):
                    return None
            except Exception:
                pass

        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                return value

        return value

    def _ensure_json_safe(self, data: dict) -> dict:
        return json.loads(
            json.dumps(
                self._make_json_safe(data),
                ensure_ascii=False,
                default=str,
            )
        )

    def _json_size(self, value) -> int:
        return len(
            json.dumps(
                self._make_json_safe(value),
                ensure_ascii=False,
                default=str,
            )
        )

    def _truncate_text(self, value, limit: int = 500):
        if not isinstance(value, str):
            return value

        if len(value) <= limit:
            return value

        return f"{value[:limit].rstrip()}..."

    def _limit_dict_lists(self, value, limit: int) -> dict:
        if not isinstance(value, dict):
            return {}

        compact = {}

        for key, items in value.items():
            if isinstance(items, list):
                compact[key] = [
                    self._truncate_text(item, 120)
                    for item in items[:limit]
                ]
            else:
                compact[key] = items

        return compact

    def _compact_schema_for_ai(self, schema: dict, unique_values_limit: int = AI_UNIQUE_VALUES_LIMIT) -> dict:
        compact = dict(schema or {})
        compact["unique_values"] = self._limit_dict_lists(
            compact.get("unique_values", {}),
            unique_values_limit,
        )

        compact_columns = []

        for column in compact.get("columns", []):
            if not isinstance(column, dict):
                compact_columns.append(column)
                continue

            compact_column = dict(column)
            compact_column["sample"] = [
                self._truncate_text(item, 120)
                for item in (compact_column.get("sample") or [])[:3]
            ]
            compact_columns.append(compact_column)

        compact["columns"] = compact_columns
        return self._make_json_safe(compact)

    def _compact_plan_for_ai(self, plan: dict, chart_limit: int | None = None) -> dict:
        compact = dict(plan or {})
        charts = compact.get("charts")

        if isinstance(charts, list):
            limited_charts = charts[:chart_limit] if chart_limit else charts
            compact["charts"] = [
                self._compact_chart_plan_for_ai(chart)
                for chart in limited_charts
                if isinstance(chart, dict)
            ]

        if "business_context" in compact:
            compact["business_context"] = self._truncate_text(
                compact.get("business_context"),
                300,
            )

        return self._make_json_safe(compact)

    def _compact_chart_plan_for_ai(self, chart_plan: dict) -> dict:
        allowed_keys = {
            "title",
            "operation",
            "chart_type",
            "group_by",
            "metric",
            "aggregation",
            "x",
            "y",
            "time_column",
            "time_freq",
            "filters",
            "limit",
            "sort",
            "reason",
        }
        compact = {
            key: value
            for key, value in chart_plan.items()
            if key in allowed_keys
        }

        if "reason" in compact:
            compact["reason"] = self._truncate_text(compact.get("reason"), 250)

        return compact

    def _compact_chart_for_ai(self, chart: dict, data_limit: int = AI_CHART_DATA_LIMIT) -> dict:
        compact = {}

        for key, value in (chart or {}).items():
            if key == "drill_down":
                drill_down = dict(value or {})
                drill_down.pop("rows", None)
                compact[key] = drill_down
                continue

            if key == "plan":
                compact[key] = self._compact_chart_plan_for_ai(value or {})
                continue

            if key == "data" and isinstance(value, list):
                compact[key] = value[:data_limit]
                compact["data_sampled"] = len(value) > data_limit
                compact["data_total_rows"] = len(value)
                continue

            if key == "reason":
                compact[key] = self._truncate_text(value, 250)
                continue

            compact[key] = value

        return self._make_json_safe(compact)

    def _build_ai_dashboard_payload(
        self,
        charts: list[dict],
        schema: dict,
        plan: dict,
    ) -> tuple[list[dict], dict, dict]:
        charts_for_ai = [
            self._compact_chart_for_ai(chart, AI_CHART_DATA_LIMIT)
            for chart in charts
        ]
        schema_for_ai = self._compact_schema_for_ai(schema, AI_UNIQUE_VALUES_LIMIT)
        plan_for_ai = self._compact_plan_for_ai(plan)

        payload = {
            "charts": charts_for_ai,
            "schema": schema_for_ai,
            "plan": plan_for_ai,
        }

        if self._json_size(payload) <= AI_PAYLOAD_MAX_CHARS:
            return charts_for_ai, schema_for_ai, plan_for_ai

        charts_for_ai = [
            self._compact_chart_for_ai(chart, AI_COMPACT_CHART_DATA_LIMIT)
            for chart in charts[:6]
        ]
        schema_for_ai = self._compact_schema_for_ai(schema, AI_COMPACT_UNIQUE_VALUES_LIMIT)
        plan_for_ai = self._compact_plan_for_ai(plan, chart_limit=6)

        payload = {
            "charts": charts_for_ai,
            "schema": schema_for_ai,
            "plan": plan_for_ai,
        }

        if self._json_size(payload) <= AI_PAYLOAD_MAX_CHARS:
            return charts_for_ai, schema_for_ai, plan_for_ai

        raise ValueError(
            "A fonte é grande demais para análise geral. "
            "Gere com um prompt mais específico ou reduza a fonte."
        )

    def _get_chart_axis(self, chart_plan: dict, operation: str) -> tuple[str | None, str | None]:
        if operation == "time_groupby":
            return "label", "value"

        if operation == "count":
            return chart_plan.get("x"), "Quantidade"

        return chart_plan.get("x"), chart_plan.get("y")

    def _normalize_name(self, value) -> str:
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        return text.replace("_", " ")

    def _find_column_by_aliases(self, columns: list[str], aliases: list[str]) -> str | None:
        normalized_aliases = [self._normalize_name(alias) for alias in aliases]

        for column in columns:
            if self._normalize_name(column) in normalized_aliases:
                return column

        for column in columns:
            normalized_column = self._normalize_name(column)

            if any(alias in normalized_column for alias in normalized_aliases):
                return column

        return None

    def _normalize_drill_hierarchy(self, df: pd.DataFrame, chart_plan: dict) -> list[dict]:
        columns = [str(column) for column in df.columns]
        requested = chart_plan.get("drill_down_hierarchy") or []
        hierarchy = []

        for column in requested:
            found = self._find_column_by_aliases(columns, [column])

            if found and found not in [item["column"] for item in hierarchy]:
                hierarchy.append({"column": found, "label": found})

        if len(hierarchy) >= 2:
            return hierarchy

        templates = [
            [
                ["regiao", "região", "region"],
                ["estado", "uf", "state"],
                ["cidade", "municipio", "city"],
            ],
            [
                ["categoria", "category", "categoria produto"],
                ["produto", "product", "item", "sku"],
            ],
        ]

        for template in templates:
            inferred = []

            for aliases in template:
                found = self._find_column_by_aliases(columns, aliases)

                if found:
                    inferred.append({"column": found, "label": found})

            if len(inferred) >= 2:
                x_column = chart_plan.get("x")
                start_index = next(
                    (
                        index for index, item in enumerate(inferred)
                        if self._normalize_name(item["column"]) == self._normalize_name(x_column)
                    ),
                    0,
                )

                sliced = inferred[start_index:]

                return sliced if len(sliced) >= 2 else inferred

        return []

    def _build_drill_down_config(self, df: pd.DataFrame, chart_plan: dict, chart_x: str | None) -> dict:
        chart_type = chart_plan.get("chart_type")

        if chart_type not in ["bar", "horizontal_bar", "line", "area", "pie", "donut", "scatter"]:
            return {"enabled": False}

        filtered_df = self.pandas_tools.filter_dataframe(
            df=df,
            filters=chart_plan.get("filters") or [],
        )

        if filtered_df.empty:
            return {"enabled": False}

        hierarchy = self._normalize_drill_hierarchy(filtered_df, chart_plan)
        time_column = chart_plan.get("time_column") if chart_plan.get("operation") == "time_groupby" else None

        if len(hierarchy) < 2 and not time_column:
            return {"enabled": False}

        metric = chart_plan.get("metric") or []
        metric_column = metric[0] if isinstance(metric, list) and metric else chart_plan.get("y")

        rows = filtered_df.head(5000).to_dict(orient="records")

        return {
            "enabled": True,
            "hierarchy": hierarchy,
            "metric_column": metric_column,
            "time_column": time_column or chart_x,
            "rows": self._make_json_safe(rows),
        }

    def analyze(self, data: dict):
        token = data.get("token")
        question = data.get("question")
        dataset = data.get("dataset")

        if not token:
            raise ValueError("token is required")

        if not question:
            raise ValueError("question is required")

        if dataset is not None and not isinstance(dataset, list):
            raise ValueError("dataset must be a list")

        if not self.accounts.valid_token(token):
            raise ValueError("invalid token")

        messages = self.accounts.get_user_conversations(token=token)

        if dataset:
            columns = list(dataset[0].keys())
            unique_values = self.pandas_tools.unique_values(
                df=pd.DataFrame(dataset),
                columns=columns,
            )

            interpretation = self.interpreter.run(
                question=question,
                columns=columns,
                messages=messages,
                unique_values=unique_values,
            )

            chart = {
                "type": "none",
                "x": None,
                "y": None,
                "data": [],
            }

            if interpretation.get("mode") == "analysis":
                chart = self.analyzer.run(
                    dataset=dataset,
                    interpretation=interpretation,
                )

            chart = self._make_json_safe(chart)
            interpretation = self._make_json_safe(interpretation)

            answer = self.generator.run(
                question=question,
                chart=chart,
                messages=messages,
                interpretation=interpretation,
            )

            return self._ensure_json_safe({
                "answer": answer,
                "chart": chart,
                "charts": [chart] if chart and chart.get("type") != "none" else [],
                "interpretation": interpretation,
            })

        answer = self.generator.run(
            question=question,
            chart=None,
            messages=messages,
            interpretation=None,
        )

        return {
            "answer": answer,
            "chart": None,
            "charts": [],
            "interpretation": None,
        }

    def chat(self, data: dict) -> dict:
        token = data["token"]
        conversation_id = data["conversation_id"]
        question = data["question"]

        if not self.accounts.valid_token(token):
            raise Exception("Token inválido.")

        messages = self.accounts.get_messages(
            token=token,
            conversation_id=conversation_id,
        )

        answer = self.generator.chat(
            question=question,
            messages=messages,
        )

        return {
            "answer": answer,
        }

    def _build_dashboard_analysis(self, data: dict) -> dict:
        token = data["token"]
        prompt = self._normalize_prompt(data.get("prompt"))

        dataset = data["dataset"]

        if not self.accounts.valid_token(token):
            raise ValueError("Token inválido.")

        if not dataset:
            raise ValueError("Dataset vazio ou inválido.")

        df = self.cleaner.clean(dataset)

        if df.empty:
            raise ValueError("Dataset sem dados após limpeza.")

        schema = self.profiler.profile(df)
        schema["unique_values"] = self.pandas_tools.unique_values(
            df=df,
            columns=schema.get("categorical_columns", []),
            limit=AI_UNIQUE_VALUES_LIMIT,
        )
        schema = self._make_json_safe(schema)
        schema_for_plan = self._compact_schema_for_ai(schema)

        plan = self.interpreter.dashboard_plan(
            prompt=prompt,
            schema=schema_for_plan,
        )

        plan = self._make_json_safe(plan)

        rename_columns = plan.get("rename_columns", {})
        chart_plans = plan.get("charts") or [plan]

        if not chart_plans:
            raise ValueError("Nenhum plano de gráfico foi gerado.")

        for chart_plan in chart_plans:
            chart_plan["rename_columns"] = rename_columns

        all_charts_data = []

        for index, chart_plan in enumerate(chart_plans):
            operation = chart_plan.get("operation")

            metrics = self.pandas_tools.execute(
                df=df,
                plan=chart_plan,
            )

            metrics = self._make_json_safe(metrics)

            chart_x, chart_y = self._get_chart_axis(
                chart_plan=chart_plan,
                operation=operation,
            )
            drill_down = self._build_drill_down_config(
                df=df,
                chart_plan=chart_plan,
                chart_x=chart_x,
            )

            all_charts_data.append({
                "index": index + 1,
                "title": chart_plan.get("title", f"Gráfico {index + 1}"),
                "chart_type": chart_plan.get("chart_type", "bar"),
                "operation": operation,
                "x": chart_x,
                "y": chart_y,
                "aggregation": chart_plan.get("aggregation"),
                "filters": chart_plan.get("filters", []),
                "drill_down": drill_down,
                "reason": chart_plan.get("reason", ""),
                "plan": self._make_json_safe(chart_plan),
                "data": metrics,
            })

        all_charts_data = self._make_json_safe(all_charts_data)
        charts_for_ai, schema_for_ai, plan_for_ai = self._build_ai_dashboard_payload(
            charts=all_charts_data,
            schema=schema,
            plan=plan,
        )

        ai_suggestion = self.generator.dashboard_analysis_multi(
            prompt=prompt,
            charts=charts_for_ai,
            schema=schema_for_ai,
            plan=plan_for_ai,
        )

        return self._ensure_json_safe({
            "charts": all_charts_data,
            "ai_suggestion": ai_suggestion,
            "plan": plan,
        })

    def analyze_dashboard_refresh(self, data: dict) -> dict:
        return self._build_dashboard_analysis(data)

    def generate_dashboard(self, data: dict) -> dict:
        token = data["token"]
        title = data["title"]
        prompt = self._normalize_prompt(data.get("prompt"))
        file_name = data.get("file_name")
        data_source_id = data.get("data_source_id")

        analysis = self._build_dashboard_analysis(data)

        dashboard = self.accounts.create_dashboard(
            token=token,
            title=title,
            prompt=prompt or "",
            ai_suggestion=analysis["ai_suggestion"],
            file_name=file_name,
            data_source_id=data_source_id,
        )

        if not dashboard:
            raise ValueError("Erro ao salvar dashboard.")

        created_charts = []

        for chart_data in analysis["charts"]:
            chart = self.accounts.create_dashboard_chart(
                dashboard_id=dashboard["id"],
                chart_type=chart_data["chart_type"],
                title=chart_data["title"],
                chart_data=chart_data["data"],
                chart_config={
                    "x": chart_data["x"],
                    "y": chart_data["y"],
                    "aggregation": chart_data["aggregation"],
                    "operation": chart_data["operation"],
                    "filters": chart_data.get("filters", []),
                    "drill_down": chart_data.get("drill_down", {"enabled": False}),
                    "reason": chart_data["reason"],
                },
            )

            if chart:
                created_charts.append(chart)

        if not created_charts:
            raise ValueError("Erro ao salvar gráficos.")

        return self._ensure_json_safe({
            "dashboard": dashboard,
            "charts": created_charts,
            "ai_suggestion": analysis["ai_suggestion"],
            "plan": analysis["plan"],
        })

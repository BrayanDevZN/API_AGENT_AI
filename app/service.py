import json
from datetime import date, datetime

import pandas as pd

from app.accounts_client import AccountsClient
from app.interpreter import Interpreter
from app.analyzer import Analyzer
from app.generator import Generator
from app.data_cleaner import DataCleaner
from app.data_profiler import DataProfiler
from app.pandas_tools import PandasTools


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

    def _get_chart_axis(self, chart_plan: dict, operation: str) -> tuple[str | None, str | None]:
        if operation == "time_groupby":
            return "label", "value"

        if operation == "count":
            return chart_plan.get("x"), "Quantidade"

        return chart_plan.get("x"), chart_plan.get("y")

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
        )
        schema = self._make_json_safe(schema)

        plan = self.interpreter.dashboard_plan(
            prompt=prompt,
            schema=schema,
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

            all_charts_data.append({
                "index": index + 1,
                "title": chart_plan.get("title", f"Gráfico {index + 1}"),
                "chart_type": chart_plan.get("chart_type", "bar"),
                "operation": operation,
                "x": chart_x,
                "y": chart_y,
                "aggregation": chart_plan.get("aggregation"),
                "filters": chart_plan.get("filters", []),
                "reason": chart_plan.get("reason", ""),
                "plan": self._make_json_safe(chart_plan),
                "data": metrics,
            })

        all_charts_data = self._make_json_safe(all_charts_data)

        ai_suggestion = self.generator.dashboard_analysis_multi(
            prompt=prompt,
            charts=all_charts_data,
            schema=schema,
            plan=plan,
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

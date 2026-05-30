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

            interpretation = self.interpreter.run(
                question=question,
                columns=columns,
                messages=messages,
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

            answer = self.generator.run(
                question=question,
                chart=chart,
                messages=messages,
                interpretation=interpretation,
            )

            return {
                "answer": answer,
                "chart": chart,
                "charts": [chart] if chart and chart.get("type") != "none" else [],
                "interpretation": interpretation,
            }

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

        valid = self.accounts.valid_token(token)

        if not valid:
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

    def generate_dashboard(self, data: dict) -> dict:
        token = data["token"]
        title = data["title"]
        prompt = data["prompt"]
        dataset = data["dataset"]
        file_name = data.get("file_name")

        if not self.accounts.valid_token(token):
            raise ValueError("Token inválido.")

        df = self.cleaner.clean(dataset)
        schema = self.profiler.profile(df)

        plan = self.interpreter.dashboard_plan(
            prompt=prompt,
            schema=schema,
        )

        rename_columns = plan.get("rename_columns", {})

        chart_plans = plan.get("charts") or [plan]

        for chart_plan in chart_plans:
            chart_plan["rename_columns"] = rename_columns

        all_charts_data = []
        for index, chart_plan in enumerate(chart_plans):
            metrics = self.pandas_tools.execute(
                df=df,
                plan=chart_plan,
            )

            operation = chart_plan.get("operation")

            chart_x = (
                "label"
                if operation == "time_groupby"
                else chart_plan.get("x")
            )

            chart_y = (
                "value"
                if operation == "time_groupby"
                else chart_plan.get("y")
            )

            all_charts_data.append({
                "index": index + 1,
                "title": chart_plan.get("title", f"Gráfico {index + 1}"),
                "chart_type": chart_plan.get("chart_type", "bar"),
                "operation": operation,
                "x": chart_x,
                "y": chart_y,
                "aggregation": chart_plan.get("aggregation"),
                "reason": chart_plan.get("reason", ""),
                "plan": chart_plan,
                "data": metrics,
            })

        ai_suggestion = self.generator.dashboard_analysis_multi(
            prompt=prompt,
            charts=all_charts_data,
            schema=schema,
            plan=plan,
        )

        dashboard = self.accounts.create_dashboard(
            token=token,
            title=title,
            prompt=prompt,
            ai_suggestion=ai_suggestion,
            file_name=file_name,
        )

        if not dashboard:
            raise ValueError("Erro ao salvar dashboard.")

        created_charts = []

        for chart_data in all_charts_data:
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
                    "reason": chart_data["reason"],
                },
            )

            if chart:
                created_charts.append(chart)

        if not created_charts:
            raise ValueError("Erro ao salvar gráficos.")

        return {
            "dashboard": dashboard,
            "charts": created_charts,
            "ai_suggestion": ai_suggestion,
            "plan": plan,
        }
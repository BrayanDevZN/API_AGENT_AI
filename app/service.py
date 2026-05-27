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
                messages=messages
            )

            chart = {
                "type": "none",
                "x": None,
                "y": None,
                "data": []
            }

            if interpretation.get("mode") == "analysis":
                chart = self.analyzer.run(
                    dataset=dataset,
                    interpretation=interpretation
                )

            answer = self.generator.run(
                question=question,
                chart=chart,
                messages=messages,
                interpretation=interpretation
            )

            return {
                "answer": answer,
                "chart": chart,
                "interpretation": interpretation
            }

        answer = self.generator.run(
            question=question,
            chart=None,
            messages=messages,
            interpretation=None
        )

        return {
            "answer": answer,
            "chart": None,
            "interpretation": None
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
            conversation_id=conversation_id
        )

        answer = self.generator.chat(
            question=question,
            messages=messages
        )

        return {
            "answer": answer
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
            schema=schema
        )

        metrics = self.pandas_tools.execute(
            df=df,
            plan=plan
        )

        ai_suggestion = self.generator.dashboard_analysis(
            prompt=prompt,
            plan=plan,
            metrics=metrics,
            schema=schema
        )

        dashboard = self.accounts.create_dashboard(
            token=token,
            title=title,
            prompt=prompt,
            ai_suggestion=ai_suggestion,
            file_name=file_name
        )

        if not dashboard:
            raise ValueError("Erro ao salvar dashboard.")

        chart = self.accounts.create_dashboard_chart(
    dashboard_id=dashboard["id"],
    chart_type=plan["chart_type"],
    title=plan["title"],
    chart_data=metrics,
    chart_config={
        "x": "periodo" if plan["operation"] == "time_groupby" else plan["x"],
        "y": "value" if plan["operation"] == "time_groupby" else plan["y"],
        "aggregation": plan["aggregation"],
        "operation": plan["operation"]
    }
)

        if not chart:
            raise ValueError("Erro ao salvar gráfico.")

        return {
            "dashboard": dashboard,
            "charts": [chart],
            "ai_suggestion": ai_suggestion
        }
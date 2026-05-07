from app.accounts_client import AccountsClient
from app.interpreter import Interpreter
from app.analyzer import Analyzer
from app.generator import Generator


class Service:
    def __init__(self):
        self.accounts = AccountsClient()
        self.interpreter = Interpreter()
        self.analyzer = Analyzer()
        self.generator = Generator()

    def analyze(self, data: dict):
        token = data.get("token")
        conversation_id = data.get("conversation_id")
        question = data.get("question")
        dataset = data.get("dataset", [])

        if not token:
            raise ValueError("token is required")

        if not conversation_id:
            raise ValueError("conversation_id is required")

        if not question:
            raise ValueError("question is required")

        if not isinstance(dataset, list):
            raise ValueError("dataset must be a list")

        if not self.accounts.valid_token(token):
            raise ValueError("invalid token")

        messages = self.accounts.get_messages(
            token=token,
            conversation_id=conversation_id
        )

        columns = list(dataset[0].keys()) if dataset else []

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
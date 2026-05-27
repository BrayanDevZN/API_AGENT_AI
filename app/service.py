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

        valid = self.accounts_client.valid_token(token)

        if not valid:
            raise Exception("Token inválido.")

        messages = self.accounts_client.get_messages(
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
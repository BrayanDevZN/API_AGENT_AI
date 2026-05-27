from app.service import Service


class Manager:
    def __init__(self):
        self.service = Service()

    def chat(self, data: dict) -> dict:
        return self.service.chat(data)

    def analyze(self, data: dict) -> dict:
        return self.service.analyze(data)

    def generate_dashboard(self, data: dict) -> dict:
        return self.service.generate_dashboard(data)
from app.service import Service


class Manager:
    def __init__(self):
        self.service = Service()

    def chat(self, data: dict) -> dict:
        return self.service.chat(data)
from app.service import Service


class Manager:
    def __init__(self):
        self.service = Service()

    def analyze(self, data: dict):
        return self.service.analyze(data)
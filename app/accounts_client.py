import requests
from core.config import settings


class AccountsClient:
    def __init__(self):
        self.base_url = settings.ACCOUNTS_API_URL.rstrip("/")

    def valid_token(self, token: str) -> bool:
        res = requests.post(
            f"{self.base_url}/valid_token",
            json={"token": token},
            timeout=settings.TIMEOUT
        )

        if res.status_code != 200:
            return False

        data = res.json()

        return (
            data.get("is_valid") is True
            or data.get("status") is True
        )

    def get_user_conversations(self, token: str) -> list:
        res = requests.post(
            f"{self.base_url}/conversation/user",
            json={"token": token},
            timeout=settings.TIMEOUT
        )

        if res.status_code != 200:
            return []

        return res.json()

    def get_messages(self, token: str, conversation_id: int) -> list:
        res = requests.post(
            f"{self.base_url}/conversation/messages",
            json={
                "token": token,
                "conversation_id": conversation_id
            },
            timeout=settings.TIMEOUT
        )

        if res.status_code != 200:
            return []

        data = res.json()

        if isinstance(data, list):
            return data

        return data.get("messages", [])
    
    def create_dashboard(
        self,
        token: str,
        title: str,
        prompt: str,
        ai_suggestion: str | None,
        file_name: str | None
    ) -> dict | None:
        res = requests.post(
            f"{self.base_url}/dashboard/create",
            json={
                "token": token,
                "title": title,
                "prompt": prompt,
                "ai_suggestion": ai_suggestion,
                "file_name": file_name
            },
            timeout=settings.TIMEOUT
        )

        if res.status_code not in (200, 201):
            return None

        return res.json().get("dashboard")


    def create_dashboard_chart(
        self,
        dashboard_id: int,
        chart_type: str,
        title: str,
        chart_data: list[dict],
        chart_config: dict | None = None
    ) -> dict | None:
        res = requests.post(
            f"{self.base_url}/dashboard/chart/create",
            json={
                "dashboard_id": dashboard_id,
                "chart_type": chart_type,
                "title": title,
                "chart_data": {
                    "data": chart_data
                },
                "chart_config": chart_config
            },
            timeout=settings.TIMEOUT
        )

        if res.status_code not in (200, 201):
            return None

        return res.json().get("chart")
    
    
    def get_data_source(
        self,
        token: str,
        data_source_id: int
    ) -> dict:
        response = requests.post(
            f"{self.base_url}/data-source",
            json={
                "token": token,
                "data_source_id": data_source_id
            },
            timeout=30
        )

        if not response.ok:
            raise Exception(response.text)

        return response.json()
import requests
from core.config import settings


class AccountsClient:
    def __init__(self):
        self.base_url = settings.ACCOUNTS_API_URL

    def valid_token(self, token: str) -> bool:
        res = requests.post(
            f"{self.base_url}/valid_token",
            json={"token": token},
            timeout=settings.TIMEOUT
        )

        if res.status_code != 200:
            return False

        data = res.json()
        return data.get("is_valid") is True

    def get_user_conversations(self, token: str) -> list:
        res = requests.post(
            f"{self.base_url}/conversation/user",
            json=token,
            timeout=settings.TIMEOUT
        )

        if res.status_code != 200:
            return []

        return res.json()

    def get_messages(self, token: str, conversation_id: int):
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

        return res.json()
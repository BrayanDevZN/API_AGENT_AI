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
        return  data.get("is_valid") is True

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
    
    
aa = AccountsClient().valid_token(token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo5LCJlbWFpbCI6InNvdXphYnJheWFuNTM0QGdtYWlsLmNvbSIsInN0YXR1cyI6ZmFsc2UsInJvbGUiOiJ1c2VyIn0.0BUHUUEO22grYiYCuAIAx-DI9uouE3trvY1lJ11YkVo")
print(aa)
from fastapi import (
    APIRouter,
    Form,
    HTTPException
)

from app.manager import Manager
from app.accounts_client import AccountsClient

from api.model import ChatRequest, ChatResponse, DashboardAnalyzeResponse


router = APIRouter()

manager = Manager()
accounts_client = AccountsClient()


@router.post("/chat", response_model=ChatResponse)
def chat(data: ChatRequest):
    try:
        return manager.chat(data.model_dump())

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@router.post("/dashboard/analyze", response_model=DashboardAnalyzeResponse)
async def dashboard_analyze(
    token: str = Form(...),
    title: str = Form(...),
    prompt: str = Form(...),
    data_source_id: int = Form(...)
):
    try:
        source_response = accounts_client.get_data_source(
            token=token,
            data_source_id=data_source_id
        )

        data_source = source_response.get("data_source")

        if not data_source:
            raise ValueError("Fonte de dados não encontrada.")

        dataset = data_source.get("file_data")

        if not dataset:
            raise ValueError("A fonte de dados não possui dados válidos.")

        data = {
            "token": token,
            "title": title,
            "prompt": prompt,
            "data_source_id": data_source_id,
            "file_name": data_source.get("file_name"),
            "dataset": dataset
        }

        return manager.generate_dashboard(data)

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
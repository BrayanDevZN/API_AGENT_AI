import traceback

from fastapi import (
    APIRouter,
    Form,
    HTTPException,
)

from app.manager import Manager
from app.accounts_client import AccountsClient

from api.model import (
    ChatRequest,
    ChatResponse,
    DashboardAnalyzeResponse,
    DashboardRefreshAnalyzeResponse,
)


router = APIRouter()

manager = Manager()
accounts_client = AccountsClient()


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {str(error)}"


def get_dashboard_data(
    token: str,
    title: str,
    prompt: str | None,
    data_source_id: int,
) -> dict:
    clean_title = title.strip() if title and title.strip() else None
    clean_prompt = prompt.strip() if prompt and prompt.strip() else None

    if not clean_title:
        raise ValueError("Nome do dashboard é obrigatório.")

    source_response = accounts_client.get_data_source(
        token=token,
        data_source_id=data_source_id,
    )

    data_source = source_response.get("data_source")

    if not data_source:
        raise ValueError("Fonte de dados não encontrada.")

    dataset = data_source.get("file_data")

    if not dataset:
        raise ValueError("A fonte de dados não possui dados válidos.")

    if not isinstance(dataset, list):
        raise ValueError("Os dados da fonte precisam estar em formato de lista.")

    return {
        "token": token,
        "title": clean_title,
        "prompt": clean_prompt,
        "data_source_id": data_source_id,
        "file_name": data_source.get("file_name"),
        "dataset": dataset,
    }


@router.post("/chat", response_model=ChatResponse)
def chat(data: ChatRequest):
    try:
        return manager.chat(data.model_dump())

    except Exception as error:
        traceback.print_exc()

        raise HTTPException(
            status_code=400,
            detail=format_error(error),
        )


@router.post("/dashboard/analyze", response_model=DashboardAnalyzeResponse)
async def dashboard_analyze(
    token: str = Form(...),
    title: str = Form(...),
    prompt: str | None = Form(None),
    data_source_id: int = Form(...),
):
    try:
        data = get_dashboard_data(
            token=token,
            title=title,
            prompt=prompt,
            data_source_id=data_source_id,
        )

        return manager.generate_dashboard(data)

    except Exception as error:
        traceback.print_exc()

        raise HTTPException(
            status_code=400,
            detail=format_error(error),
        )


@router.post("/dashboard/refresh/analyze", response_model=DashboardRefreshAnalyzeResponse)
async def dashboard_refresh_analyze(
    token: str = Form(...),
    title: str = Form(...),
    prompt: str | None = Form(None),
    data_source_id: int = Form(...),
):
    try:
        data = get_dashboard_data(
            token=token,
            title=title,
            prompt=prompt,
            data_source_id=data_source_id,
        )

        return manager.analyze_dashboard_refresh(data)

    except Exception as error:
        traceback.print_exc()

        raise HTTPException(
            status_code=400,
            detail=format_error(error),
        )

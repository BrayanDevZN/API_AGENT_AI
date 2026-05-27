from fastapi import APIRouter, HTTPException

from app.manager import Manager
from api.model import ChatRequest, ChatResponse


router = APIRouter()

manager = Manager()


@router.post(
    "/chat",
    response_model=ChatResponse
)
def chat(data: ChatRequest):
    try:
        result = manager.chat(data.model_dump())
        return result

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException
)

from app.manager import Manager
from app.file_reader import FileReader

from api.model import ChatRequest, ChatResponse, DashboardAnalyzeResponse


router = APIRouter()

manager = Manager()
reader = FileReader()


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
    file: UploadFile = File(...)
):
    try:
        dataset = await reader.read(file)

        data = {
            "token": token,
            "title": title,
            "prompt": prompt,
            "file_name": file.filename,
            "dataset": dataset
        }

        return manager.generate_dashboard(data)

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
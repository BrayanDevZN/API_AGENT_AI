from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException
)

from app.manager import Manager
from app.file_reader import FileReader

from api.model import (
    AnalyzeJsonRequest,
    AnalyzeResponse
)


router = APIRouter()

manager = Manager()
reader = FileReader()


@router.post(
    "/analyze/json",
    response_model=AnalyzeResponse
)
def analyze_json(data: AnalyzeJsonRequest):

    try:
        result = manager.analyze(data.model_dump())
        return result

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@router.post(
    "/analyze/file",
    response_model=AnalyzeResponse
)
async def analyze_file(
    file: UploadFile = File(...),
    token: str = Form(...),
    conversation_id: int = Form(...),
    question: str = Form(...)
):

    try:
        dataset = await reader.read(file)

        data = {
            "token": token,
            "conversation_id": conversation_id,
            "question": question,
            "dataset": dataset
        }

        result = manager.analyze(data)

        return result

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
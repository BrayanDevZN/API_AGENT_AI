from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException
)

from app.manager import Manager
from app.file_reader import FileReader

from api.model import AnalyzeResponse


router = APIRouter()

manager = Manager()
reader = FileReader()


@router.post(
    "/chat",
    response_model=AnalyzeResponse
)
async def chat(
    token: str = Form(...),
    question: str = Form(...),
    file: UploadFile | None = File(None)
):
    try:
        dataset = None

        if file is not None:
            dataset = await reader.read(file)

        data = {
            "token": token,
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
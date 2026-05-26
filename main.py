from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import Settings
from api.routes import router


app = FastAPI(
    title="AI Data Analysis API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://datapilotplataform.com",
        "https://www.datapilotplataform.com",
        Settings().ACCOUNTS_API_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
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
    allow_origins=Settings().CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)

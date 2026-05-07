from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router


app = FastAPI(
    title="AI Data Analysis API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://web-production-40ead.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
from fastapi import FastAPI

from api.routes import router


app = FastAPI(
    title="AI Data Analysis API",
    version="1.0.0"
)


app.include_router(router)
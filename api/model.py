from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class AnalyzeJsonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1)
    conversation_id: int = Field(gt=0)
    question: str = Field(min_length=1)
    dataset: list[dict] = Field(default_factory=list)

    @field_validator("token", "question")
    @classmethod
    def not_empty(cls, value: str):
        if not value.strip():
            raise ValueError("field cannot be empty")
        return value


class AnalyzeResponse(BaseModel):
    answer: str
    chart: Optional[dict[str, Any]] = None
    charts: list[dict[str, Any]] = Field(default_factory=list)
    interpretation: Optional[dict[str, Any]] = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1)
    conversation_id: int = Field(gt=0)
    question: str = Field(min_length=1)

    @field_validator("token", "question")
    @classmethod
    def not_empty(cls, value: str):
        if not value.strip():
            raise ValueError("field cannot be empty")
        return value


class ChatResponse(BaseModel):
    answer: str


class DashboardAnalyzeResponse(BaseModel):
    dashboard: dict[str, Any]
    charts: list[dict[str, Any]]
    ai_suggestion: str
    plan: Optional[dict[str, Any]] = None


class DashboardRefreshAnalyzeResponse(BaseModel):
    charts: list[dict[str, Any]]
    ai_suggestion: str
    plan: Optional[dict[str, Any]] = None

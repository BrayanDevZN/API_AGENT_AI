from pydantic import BaseModel, Field, ConfigDict, field_validator


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
    chart: dict
    interpretation: dict
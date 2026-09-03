from pydantic import BaseModel


class MCQOut(BaseModel):
    question: str
    options: list[str]
    correct_answer: str
    explanation: str


class GenerateResponse(BaseModel):
    summary: str
    key_points: list[str]
    mcqs: list[MCQOut]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail

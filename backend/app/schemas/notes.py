import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt: str
    options: list[str]
    correct_option_index: int
    explanation: str


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    questions: list[QuestionOut]


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_filename: str
    language: str
    summary: str
    key_points: list[str]
    created_at: datetime
    quiz: QuizOut | None = None


class NoteListResponse(BaseModel):
    notes: list[NoteOut]
    limit: int
    offset: int

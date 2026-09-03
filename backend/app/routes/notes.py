"""v2 endpoints — auth-required, persisted. Reuses the exact same generation
services as the v1 MVP endpoint, then adds ownership + storage on top."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_id
from app.config import get_settings
from app.db import get_session
from app.repositories.notes_repository import NotesRepository
from app.schemas.notes import NoteListResponse, NoteOut
from app.services.llm_client import LLMGenerationError, generate_structured
from app.services.mcq_validator import validate_and_filter_mcqs
from app.services.pdf_extractor import PDFExtractionError, ScannedPDFError, extract_text
from app.services.prompt_builder import build_prompt

router = APIRouter(prefix="/api/v2/notes", tags=["notes"])

ALLOWED_LANGUAGES = {"en", "hi", "bn"}


@router.post("", response_model=NoteOut, status_code=201)
async def create_note(
    file: UploadFile = File(...),
    language: str = Form(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Generates AND persists a note+quiz for the logged-in user — the v2
    counterpart of the stateless POST /api/v1/generate."""
    settings = get_settings()

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_FILE_TYPE", "message": "Only PDF files are accepted."}},
        )
    if language not in ALLOWED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_LANGUAGE",
                    "message": f"Language must be one of {sorted(ALLOWED_LANGUAGES)}.",
                }
            },
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail={"error": {"code": "FILE_TOO_LARGE", "message": "File exceeds the 15MB limit."}},
        )

    try:
        lecture_text = extract_text(file_bytes, settings.min_extracted_text_chars)
    except ScannedPDFError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "NO_EXTRACTABLE_TEXT", "message": str(exc)}},
        ) from exc
    except PDFExtractionError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "PDF_READ_ERROR", "message": str(exc)}},
        ) from exc

    system_prompt, user_prompt = build_prompt(
        lecture_text, language, settings.min_mcqs, settings.max_mcqs, settings.max_prompt_chars
    )
    try:
        result = generate_structured(system_prompt, user_prompt, retries=1)
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": "LLM_GENERATION_FAILED",
                    "message": "Could not generate notes right now. Please try again.",
                }
            },
        ) from exc

    valid_mcqs = validate_and_filter_mcqs(result.get("mcqs", []))

    repo = NotesRepository(session)
    note = await repo.create_with_quiz(
        user_id=user_id,
        source_filename=file.filename or "untitled.pdf",
        language=language,
        summary=result["summary"],
        key_points=result["key_points"],
        mcqs=valid_mcqs,
    )
    return note


@router.get("", response_model=NoteListResponse)
async def list_notes(
    search: str | None = Query(
        default=None, description="Full-text search across filename and summary (PRD FR-f)"
    ),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Dashboard query — 'show my notes, most recent first', optionally
    filtered by search (backs idx_notes_user_created / idx_notes_search)."""
    repo = NotesRepository(session)
    notes = await repo.list_for_user(user_id, search, limit, offset)
    return NoteListResponse(notes=notes, limit=limit, offset=offset)


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(
    note_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    repo = NotesRepository(session)
    note = await repo.get_for_user(note_id, user_id)
    if note is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Note not found."}},
        )
    return note

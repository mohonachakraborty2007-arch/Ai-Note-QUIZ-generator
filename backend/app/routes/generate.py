"""v1 MVP endpoint — stateless, no auth, no database.

This is the actual 1-day MVP core: a single request that uploads a PDF,
extracts text, generates a summary/key points/quiz via one LLM call, and
returns the result. Nothing here is persisted.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.schemas.generation import GenerateResponse
from app.services.llm_client import LLMGenerationError, generate_structured
from app.services.mcq_validator import validate_and_filter_mcqs
from app.services.pdf_extractor import PDFExtractionError, ScannedPDFError, extract_text
from app.services.prompt_builder import build_prompt

router = APIRouter(prefix="/api/v1", tags=["generate"])

ALLOWED_LANGUAGES = {"en", "hi", "bn"}


@router.post("/generate", response_model=GenerateResponse)
async def generate_notes_and_quiz(
    file: UploadFile = File(...),
    language: str = Form(...),
):
    settings = get_settings()

    # FR-1.2: reject non-PDF files
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_FILE_TYPE",
                    "message": "Only PDF files are accepted.",
                }
            },
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

    # FR-1.3: reject oversized files
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": "File exceeds the 15MB limit.",
                }
            },
        )

    # FR-1.4 / FR-1.5: extract text, detect likely-scanned PDFs
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

    # FR-3.1 / FR-3.2 / FR-3.3: build the prompt, call the LLM, retry once on bad JSON
    system_prompt, user_prompt = build_prompt(
        lecture_text,
        language,
        settings.min_mcqs,
        settings.max_mcqs,
        settings.max_prompt_chars,
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

    # FR-3.5: hard validation gate — MCQs failing self-check are dropped, not shown
    result["mcqs"] = validate_and_filter_mcqs(result.get("mcqs", []))

    return GenerateResponse(**result)

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # v2 database (unused by the v1 stateless /generate endpoint)
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/lecture_notes"
    )

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # v2 auth
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # PRD FR-1.3: reject files over this size
    max_upload_size_bytes: int = 15 * 1024 * 1024  # 15MB

    # PRD FR-1.5: below this many extracted characters, treat as a likely scanned PDF
    min_extracted_text_chars: int = 200

    # PRD FR-3.1: truncation budget for the LLM prompt (simple truncation for v1;
    # chunk-then-combine documented in architecture.md as a "with more time" improvement)
    max_prompt_chars: int = 40_000

    # PRD FR-3.4
    min_mcqs: int = 5
    max_mcqs: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()

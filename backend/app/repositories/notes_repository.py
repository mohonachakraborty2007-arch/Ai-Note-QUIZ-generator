"""All database access for notes/quizzes/questions lives here — routes never
construct queries directly. This is where the idx_notes_user_created and
idx_notes_search indexes from /db/schema.sql actually get exercised."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note, Question, Quiz


class NotesRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_with_quiz(
        self,
        user_id: uuid.UUID,
        source_filename: str,
        language: str,
        summary: str,
        key_points: list[str],
        mcqs: list[dict],
    ) -> Note:
        """Persists a Note, its Quiz, and all Questions in a single
        transaction — the DB-level counterpart to FR-3.5's app-level MCQ
        validation gate (the correct_index_in_range CHECK constraint is the
        final backstop)."""
        note = Note(
            user_id=user_id,
            source_filename=source_filename,
            language=language,
            summary=summary,
            key_points=key_points,
        )
        quiz = Quiz(note=note)
        for mcq in mcqs:
            options = mcq["options"]
            quiz.questions.append(
                Question(
                    prompt=mcq["question"],
                    options=options,
                    correct_option_index=options.index(mcq["correct_answer"]),
                    explanation=mcq["explanation"],
                )
            )

        self.session.add(note)
        await self.session.commit()
        await self.session.refresh(note)
        return note

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[Note]:
        """Dashboard query (PRD FR-e/f): most-recent-first, optionally
        filtered by a search term across filename and summary."""
        stmt = select(Note).where(Note.user_id == user_id)

        if search:
            like_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Note.source_filename.ilike(like_pattern),
                    Note.summary.ilike(like_pattern),
                )
            )

        stmt = stmt.order_by(Note.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_user(self, note_id: uuid.UUID, user_id: uuid.UUID) -> Note | None:
        """Returns the note only if it belongs to user_id — ownership
        enforced here, not left to the caller (see api-spec.md Section 4)."""
        stmt = select(Note).where(Note.id == note_id, Note.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

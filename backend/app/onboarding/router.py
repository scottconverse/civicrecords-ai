"""Onboarding LLM-guided adaptive interview endpoint.

The interview endpoint generates the next setup question based on what
fields in the city profile are already completed. It does NOT update the
profile — that happens via the frontend calling PATCH /city-profile with
the user's answer.
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_async_session
from app.llm.client import generate
from app.models.city_profile import CityProfile
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Fields we want the interview to cover, in priority order
# Must match actual CityProfile model fields in app/models/city_profile.py
_PROFILE_FIELDS = [
    ("city_name", "What is the name of your city or municipality?"),
    ("state", "Which US state is your municipality in? (two-letter code, e.g. CO)"),
    ("county", "What county is your municipality in?"),
    ("population_band", "What is your municipality's approximate population? (Under 5,000 / 5,000-25,000 / 25,000-100,000 / 100,000-500,000 / Over 500,000)"),
    ("email_platform", "What email platform does your municipality use? (Microsoft 365, Google Workspace, or other)"),
    ("monthly_request_volume", "How many public records requests does your office handle per month on average?"),
]

_SYSTEM_PROMPT = """You are a friendly municipal records system setup assistant. Your job is
to help a city clerk configure CivicRecords AI for their municipality.

Ask ONE question at a time. Be conversational but concise. If the user's
previous answer was unclear, ask a brief clarifying follow-up. Otherwise,
move to the next incomplete field.

Do NOT update any settings yourself — just ask the question and wait for the answer.
Keep responses under 3 sentences."""


class InterviewRequest(BaseModel):
    last_answer: str | None = None
    last_field: str | None = None


class InterviewResponse(BaseModel):
    question: str
    target_field: str | None  # The profile field this question targets, or None if all complete
    all_complete: bool
    completed_fields: list[str]


@router.post("/interview", response_model=InterviewResponse)
async def get_next_question(
    body: InterviewRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Generate the next onboarding interview question.

    Inspects the current city profile to determine which fields are still
    empty, then generates a contextual question for the next incomplete field.
    Does NOT update the profile — the frontend does that via PATCH /city-profile.
    """
    # Load current profile state
    result = await session.execute(select(CityProfile).limit(1))
    profile = result.scalar_one_or_none()

    # Determine which fields are complete
    completed = []
    next_field = None
    next_default_question = None

    for field_name, default_question in _PROFILE_FIELDS:
        value = getattr(profile, field_name, None) if profile else None
        if value and str(value).strip():
            completed.append(field_name)
        elif next_field is None:
            next_field = field_name
            next_default_question = default_question

    if next_field is None:
        return InterviewResponse(
            question="Your city profile is complete! You can review your settings on the City Profile page.",
            target_field=None,
            all_complete=True,
            completed_fields=completed,
        )

    # Generate contextual question via LLM
    context_parts = [f"Completed fields: {', '.join(completed) if completed else 'none yet'}"]
    if profile and profile.city_name:
        context_parts.append(f"City: {profile.city_name}")
    if body.last_answer and body.last_field:
        context_parts.append(f"User just answered '{body.last_answer}' for the '{body.last_field}' field")
    context_parts.append(f"Next field to ask about: {next_field}")
    context_parts.append(f"Default question: {next_default_question}")

    try:
        question = await generate(
            system_prompt=_SYSTEM_PROMPT,
            user_content="\n".join(context_parts),
        )
        # Fallback if LLM returns empty
        if not question.strip():
            question = next_default_question
    except Exception:
        logger.exception("LLM interview question generation failed")
        question = next_default_question

    return InterviewResponse(
        question=question.strip(),
        target_field=next_field,
        all_complete=False,
        completed_fields=completed,
    )

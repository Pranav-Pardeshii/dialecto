from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from app.ai.llm.router import LLMUnavailableError, router
from app.schemas.practice import AIFallbackMeta

logger = structlog.get_logger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "student_persona.md"


class PipReplyResult(BaseModel):
    pip_reply: str = Field(..., description="Pip's 2-3 sentence dialogue reply in character")
    pip_mood: str = Field(
        ..., description="Pip's emotional state (confused, curious, connecting, excited)"
    )


FALLBACK_REPLIES: dict[int, str] = {
    0: "Wait, I'm still really mixed up! Could you explain the very first step again simply?",
    1: "Oh, that makes some sense! But wait, where do the raw materials actually go during this reaction?",
    2: "I think I see how they connect! So if that happens, what is the final product formed?",
    3: "Aha! I completely get it now! Thank you so much, that totally cleared up how the whole process works!",
}


async def generate_pip_reply(
    concept_name: str,
    current_level: int,
    dialog_history: list[dict[str, str]],
    tutor_message: str,
) -> tuple[PipReplyResult, AIFallbackMeta]:
    """Generates Pip's dialogue reflecting the backend-calibrated comprehension level."""
    history_text = "\n".join(
        f"{turn.get('role', 'speaker').capitalize()}: {turn.get('content', '')}"
        for turn in dialog_history
    )
    if not history_text:
        history_text = "Beginning of tutorial session."

    try:
        template = PROMPT_FILE.read_text(encoding="utf-8")
        prompt = (
            template.replace("{{ concept_name }}", concept_name)
            .replace("{{ current_level }}", str(current_level))
            .replace("{{ dialog_history }}", history_text)
            .replace("{{ tutor_message }}", tutor_message.strip())
        )

        messages = [
            {
                "role": "system",
                "content": "You are Pip, a friendly, naive Class 10 student being tutored.",
            },
            {"role": "user", "content": prompt},
        ]

        result, meta = await router.complete(
            purpose="teachback_persona",
            messages=messages,
            schema=PipReplyResult,
            max_tokens=250,
            temperature=0.4,
            timeout=10.0,
            reasoning_effort="low",
        )

        assert isinstance(result, PipReplyResult)
        return result, meta

    except LLMUnavailableError as exc:
        logger.warning("pip_persona_llm_unavailable_using_fallback", error=str(exc))
        mood = (
            "excited"
            if current_level == 3
            else "connecting"
            if current_level == 2
            else "curious"
            if current_level == 1
            else "confused"
        )
        fallback_result = PipReplyResult(
            pip_reply=FALLBACK_REPLIES.get(current_level, FALLBACK_REPLIES[0]),
            pip_mood=mood,
        )
        return fallback_result, AIFallbackMeta(used=False, model="persona-fallback", fallback=True)

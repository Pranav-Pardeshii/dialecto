from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.ai.llm.router import LLMUnavailableError, router
from app.schemas.practice import AIFallbackMeta

logger = structlog.get_logger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "misconception_classifier.md"


class MisconceptionClassificationResult(BaseModel):
    misconception_detected: bool = Field(
        ..., description="Whether a misconception was identified in the reasoning"
    )
    misconception_id: str | None = Field(
        None, description="Known misconception slug if matched, otherwise null"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence of the diagnosis from 0.0 to 1.0"
    )
    student_gap_summary: str = Field(
        ..., description="1-sentence explanation of the conceptual flaw"
    )
    remedial_nudge: str = Field(
        ..., description="Guiding hint steering the learner toward the correct mechanism"
    )


async def classify_misconception(
    stem: str,
    options: list[dict[str, Any]],
    selected_key: str,
    correct_key: str,
    student_reasoning: str,
    possible_misconceptions: list[dict[str, str]],
    deterministic_misconception_id: str | None = None,
) -> tuple[MisconceptionClassificationResult, AIFallbackMeta]:
    """Analyzes student reasoning with the LLM router to diagnose misconceptions.

    Degrades gracefully to deterministic distractor tag if LLM is unavailable.
    """
    options_text = "\n".join(
        f"- Option {opt.get('key', '')}: {opt.get('text', '')}" for opt in options
    )
    selected_text = next(
        (opt.get("text", "") for opt in options if opt.get("key") == selected_key),
        "",
    )

    misconceptions_text = (
        "\n".join(
            f"- ID: {m.get('id', '')} | Flaw: {m.get('statement', '')} | Correct: {m.get('correction', '')}"
            for m in possible_misconceptions
        )
        if possible_misconceptions
        else "No predefined misconceptions registered for this concept."
    )

    try:
        template = PROMPT_FILE.read_text(encoding="utf-8")
        prompt = (
            template.replace("{{ stem }}", stem)
            .replace("{{ options }}", options_text)
            .replace("{{ selected_key }}", selected_key)
            .replace("{{ selected_text }}", selected_text)
            .replace("{{ correct_key }}", correct_key)
            .replace("{{ possible_misconceptions }}", misconceptions_text)
            .replace("{{ student_reasoning }}", student_reasoning.strip())
        )

        messages = [
            {
                "role": "system",
                "content": "You are a precise CBSE Class 10 Biology educational diagnostician.",
            },
            {"role": "user", "content": prompt},
        ]

        result, meta = await router.complete(
            purpose="misconception_classifier",
            messages=messages,
            schema=MisconceptionClassificationResult,
            max_tokens=400,
            temperature=0.1,
            timeout=10.0,
        )

        assert isinstance(result, MisconceptionClassificationResult)
        return result, meta

    except LLMUnavailableError as exc:
        logger.warning(
            "misconception_classifier_llm_unavailable_degrading",
            error=str(exc),
            deterministic_id=deterministic_misconception_id,
        )
        # Deterministic graceful degradation
        if deterministic_misconception_id:
            return (
                MisconceptionClassificationResult(
                    misconception_detected=True,
                    misconception_id=deterministic_misconception_id,
                    confidence=0.70,
                    student_gap_summary="Answer matches a common conceptual confusion identified in the curriculum.",
                    remedial_nudge="Review how this process operates step-by-step in your textbook.",
                ),
                AIFallbackMeta(used=False, model="deterministic-rule", fallback=True),
            )

        return (
            MisconceptionClassificationResult(
                misconception_detected=False,
                misconception_id=None,
                confidence=0.50,
                student_gap_summary="Conceptual error identified from incorrect option selection.",
                remedial_nudge="Re-read the question carefully and check the underlying definition.",
            ),
            AIFallbackMeta(used=False, model="deterministic-rule", fallback=True),
        )

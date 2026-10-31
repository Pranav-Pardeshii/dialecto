from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from app.ai.llm.router import LLMUnavailableError, router
from app.schemas.practice import AIFallbackMeta

logger = structlog.get_logger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "judge.md"


class MisconceptionItem(BaseModel):
    id: str
    statement: str


class JudgeResult(BaseModel):
    comprehension_level: int = Field(..., ge=0, le=3)
    accuracy_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    covered_points: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    misconceptions_found: list[MisconceptionItem] = Field(default_factory=list)
    feedback_summary: str


async def judge_explanation(
    concept_name: str,
    chapter: str,
    rubric_points: list[str],
    known_misconceptions: list[dict[str, str]],
    student_explanation: str,
) -> tuple[JudgeResult, AIFallbackMeta]:
    """Judges learner Teach-Back explanation against verified NCERT rubric key points."""
    rubric_text = "\n".join(f"- {pt}" for pt in rubric_points)
    misconceptions_text = (
        "\n".join(f"- [{m.get('id', '')}]: {m.get('statement', '')}" for m in known_misconceptions)
        if known_misconceptions
        else "None registered."
    )

    try:
        template = PROMPT_FILE.read_text(encoding="utf-8")
        prompt = (
            template.replace("{{ concept_name }}", concept_name)
            .replace("{{ chapter }}", chapter)
            .replace("{{ rubric_points }}", rubric_text)
            .replace("{{ known_misconceptions }}", misconceptions_text)
            .replace("{{ student_explanation }}", student_explanation.strip())
        )

        messages = [
            {
                "role": "system",
                "content": "You are a precise CBSE Class 10 Biology educational evaluator.",
            },
            {"role": "user", "content": prompt},
        ]

        result, meta = await router.complete(
            purpose="teachback_judge",
            messages=messages,
            schema=JudgeResult,
            max_tokens=600,
            temperature=0.1,
            timeout=12.0,
            reasoning_effort="medium",
        )

        assert isinstance(result, JudgeResult)
        return result, meta

    except LLMUnavailableError as exc:
        logger.warning("judge_llm_unavailable_using_rule_fallback", error=str(exc))
        # Rule-based fallback based on keyword coverage
        explanation_lower = student_explanation.lower()
        covered: list[str] = []
        missing: list[str] = []

        for pt in rubric_points:
            words = [w.lower() for w in pt.split() if len(w) > 3]
            match_count = sum(1 for w in words if w in explanation_lower)
            if words and (match_count / len(words)) >= 0.4:
                covered.append(pt)
            else:
                missing.append(pt)

        coverage_ratio = len(covered) / len(rubric_points) if rubric_points else 0.5
        level = (
            3
            if coverage_ratio >= 0.8
            else 2
            if coverage_ratio >= 0.5
            else 1
            if coverage_ratio > 0.2
            else 0
        )

        fallback_result = JudgeResult(
            comprehension_level=level,
            accuracy_score=round(coverage_ratio, 2),
            confidence=0.60,
            covered_points=covered,
            missing_points=missing,
            misconceptions_found=[],
            feedback_summary="Evaluated through standard rubric keyword verification.",
        )
        return fallback_result, AIFallbackMeta(used=False, model="rule-evaluator", fallback=True)

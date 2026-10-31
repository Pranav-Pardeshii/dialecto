import argparse
import asyncio
import json
import sys
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from app.ai.llm.router import router
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
CONTENT_DIR = Path(__file__).parent.parent / "app" / "content"


class OptionItem(BaseModel):
    key: str
    text: str
    misconception_id: str | None = None


class GeneratedQuestion(BaseModel):
    id: str
    concept_id: str
    kind: str = "mcq"
    stem: str
    options: list[OptionItem]
    correct_key: str
    explanation: str
    difficulty_bucket: int = Field(ge=1, le=3)
    difficulty_rating: float = 0.0
    n_attempts: int = 0
    verified: bool = False
    source: str = "llm"


class GenerationBatch(BaseModel):
    questions: list[GeneratedQuestion]


async def generate_for_concept(concept: dict, count: int, misconceptions: list[dict]) -> list[dict]:
    concept_miscs = [m for m in misconceptions if m.get("concept_id") == concept["id"]]
    prompt = f"""Generate {count} multiple choice questions for CBSE Class 10 Biology on the following concept:
Concept: {concept['name']} ({concept['id']})
Chapter: {concept['chapter']}
Description: {concept['description']}
Key Points: {json.dumps(concept.get('key_points', []))}
Known Misconceptions: {json.dumps(concept_miscs)}

Requirements:
1. Each question must have exactly 4 options with keys "A", "B", "C", "D".
2. Vary the correct answer key evenly across A, B, C, D. Do not default to B.
3. If an option targets a known misconception, set misconception_id to that misconception's ID.
4. Difficulty bucket should range from 1 (easy) to 3 (challenging).
5. All generated items must have verified=false and source="llm".
"""
    messages = [
        {"role": "system", "content": "You are a CBSE Class 10 Biology item writer. Output strictly valid JSON."},
        {"role": "user", "content": prompt},
    ]

    res, _ = await router.complete(
        purpose="question_generation",
        messages=messages,
        schema=GenerationBatch,
        max_tokens=2000,
        temperature=0.3,
    )
    if isinstance(res, GenerationBatch):
        return [q.model_dump() for q in res.questions]
    return []


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate offline question bank with dual-model verification"
    )
    parser.add_argument(
        "--concept", type=str, default=None, help="Generate for a specific concept slug"
    )
    parser.add_argument("--count", type=int, default=6, help="Target questions per concept")
    args = parser.parse_args()

    settings = get_settings()

    # Fail explicitly if valid model credentials are unavailable
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "mock-key":
        logger.error("groq_api_key_missing_or_mock")
        print(
            "ERROR: Valid GROQ_API_KEY environment variable is required to generate questions. "
            "Mock credentials cannot be used for question generation.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(CONTENT_DIR / "concepts.json", encoding="utf-8") as f:
        concepts = json.load(f)
    with open(CONTENT_DIR / "misconceptions.json", encoding="utf-8") as f:
        misconceptions = json.load(f)

    target_concepts = concepts
    if args.concept:
        target_concepts = [c for c in concepts if c["id"] == args.concept]
        if not target_concepts:
            print(f"ERROR: Concept '{args.concept}' not found in concepts.json", file=sys.stderr)
            sys.exit(1)

    logger.info(
        "generating_questions_batch",
        target_concepts=len(target_concepts),
        count_per_concept=args.count,
    )

    generated_pool: list[dict] = []
    for c in target_concepts:
        try:
            questions = await generate_for_concept(c, args.count, misconceptions)
            generated_pool.extend(questions)
            logger.info("concept_questions_generated", concept_id=c["id"], count=len(questions))
        except Exception as exc:
            logger.error("concept_generation_failed", concept_id=c["id"], error=str(exc))

    output_path = CONTENT_DIR / "generated_questions_pending_review.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(generated_pool, f, indent=2)

    logger.info("question_generation_complete", saved_to=str(output_path), total=len(generated_pool))


if __name__ == "__main__":
    asyncio.run(main())

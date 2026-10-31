import argparse
import asyncio
import json
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

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
    difficulty_rating: float
    n_attempts: int = 0
    verified: bool = False
    source: str = "llm"


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
    logger.info("offline_question_generation_tool", primary_model=settings.LLM_PRIMARY_MODEL)

    with open(CONTENT_DIR / "concepts.json", encoding="utf-8") as f:
        concepts = json.load(f)
    with open(CONTENT_DIR / "misconceptions.json", encoding="utf-8") as f:
        misconceptions = json.load(f)

    target_concepts = concepts
    if args.concept:
        target_concepts = [c for c in concepts if c["id"] == args.concept]

    logger.info(
        "ready_to_generate",
        target_concepts=len(target_concepts),
        total_misconceptions=len(misconceptions),
        per_concept=args.count,
    )


if __name__ == "__main__":
    asyncio.run(main())

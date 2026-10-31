from app.domain.question_validator import QuestionValidator


def test_question_validator_valid_mcq() -> None:
    errors = QuestionValidator.validate_question(
        stem="During photosynthesis, photolysis of water occurs in which cellular organelle?",
        kind="mcq",
        options=[
            {"key": "A", "text": "Chloroplast"},
            {"key": "B", "text": "Mitochondria"},
            {"key": "C", "text": "Ribosome"},
            {"key": "D", "text": "Golgi apparatus"},
        ],
        correct_key="A",
        explanation="Photolysis takes place inside the thylakoid lumen of chloroplasts in the presence of light.",
        difficulty_bucket=2,
        concept_id="lp-photosynthesis",
    )
    assert errors == []


def test_question_validator_missing_correct_key() -> None:
    errors = QuestionValidator.validate_question(
        stem="Which gas is released during photosynthesis in plants?",
        kind="mcq",
        options=[
            {"key": "A", "text": "Carbon dioxide"},
            {"key": "B", "text": "Oxygen"},
        ],
        correct_key="C",  # Not in options
        explanation="Oxygen is released from splitting water molecules.",
        difficulty_bucket=1,
        concept_id="lp-photosynthesis",
    )
    assert any("does not exist among option keys" in err for err in errors)


def test_question_validator_invalid_bucket() -> None:
    errors = QuestionValidator.validate_question(
        stem="Valid stem of question with sufficient character length?",
        kind="mcq",
        options=[
            {"key": "A", "text": "Option 1"},
            {"key": "B", "text": "Option 2"},
        ],
        correct_key="A",
        explanation="Scientific explanation with adequate length.",
        difficulty_bucket=5,  # Invalid
        concept_id="lp-photosynthesis",
    )
    assert any("Difficulty bucket must be 1" in err for err in errors)


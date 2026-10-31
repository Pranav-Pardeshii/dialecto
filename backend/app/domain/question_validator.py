"""Question validation domain logic.

Pure, deterministic validator for curriculum questions.
Ensures CBSE Class 10 Biology standards, valid options, correct answer keys,
and prevents cross-concept misconception associations.
"""

from typing import Any


class QuestionValidationError(Exception):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


class QuestionValidator:
    SUPPORTED_KINDS = {
        "mcq",
        "assertion_reason",
        "case_based",
        "application",
        "diagram_id",
        "short_answer",
    }

    @classmethod
    def validate_question(
        cls,
        stem: str,
        kind: str,
        options: list[dict[str, Any]] | None,
        correct_key: str,
        explanation: str,
        difficulty_bucket: int,
        concept_id: str,
        valid_concept_misconception_ids: set[str] | None = None,
        existing_stems: set[str] | None = None,
    ) -> list[str]:
        """Validates question content against strict pedagogical and scientific rules.

        Returns a list of error strings. Empty list indicates completely valid.
        """
        errors: list[str] = []

        # 1. Stem validation
        stem_clean = stem.strip() if stem else ""
        if len(stem_clean) < 15:
            errors.append("Question stem must be at least 15 characters long.")

        if existing_stems and stem_clean.lower() in existing_stems:
            errors.append("A duplicate question with identical or near-identical text already exists.")

        # 2. Kind validation
        if kind not in cls.SUPPORTED_KINDS:
            errors.append(f"Question kind '{kind}' is unsupported. Allowed: {sorted(cls.SUPPORTED_KINDS)}")

        # 3. Difficulty validation
        if difficulty_bucket not in (1, 2, 3):
            errors.append(f"Difficulty bucket must be 1 (Foundation), 2 (Standard), or 3 (Advanced). Got {difficulty_bucket}.")

        # 4. Explanation validation
        if not explanation or len(explanation.strip()) < 10:
            errors.append("Scientific explanation must be provided (at least 10 characters).")

        # 5. Options and Correct Key validation
        if kind in ("mcq", "assertion_reason", "case_based", "application", "diagram_id"):
            if not options or len(options) < 2:
                errors.append(f"Question of kind '{kind}' must provide at least 2 answer options.")
            else:
                option_keys: set[str] = set()
                option_texts: list[str] = []
                for opt in options:
                    if not isinstance(opt, dict):
                        errors.append("Each option must be a structured object with 'key' and 'text'.")
                        continue
                    key = str(opt.get("key", "")).strip().upper()
                    text = str(opt.get("text", "")).strip()

                    if not key:
                        errors.append("Option key cannot be empty.")
                    elif key in option_keys:
                        errors.append(f"Duplicate option key '{key}' found.")
                    option_keys.add(key)

                    if not text:
                        errors.append(f"Option text for '{key}' cannot be empty.")
                    option_texts.append(text.lower())

                    # Check misconception mapping
                    misc_id = opt.get("misconception_id")
                    if misc_id and valid_concept_misconception_ids is not None:
                        if misc_id not in valid_concept_misconception_ids:
                            errors.append(
                                f"Option '{key}' targets misconception '{misc_id}' which does not belong to concept '{concept_id}'."
                            )

                # Check duplicate option text
                if len(option_texts) != len(set(option_texts)):
                    errors.append("Options contain duplicate text across choices.")

                # Check correct_key exists in option keys
                ck = correct_key.strip().upper() if correct_key else ""
                if not ck:
                    errors.append("A correct answer key must be designated.")
                elif ck not in option_keys:
                    errors.append(f"Correct key '{ck}' does not exist among option keys {sorted(option_keys)}.")

        elif kind == "short_answer":
            if not correct_key or len(correct_key.strip()) < 1:
                errors.append("Short answer questions must provide the canonical model answer in correct_key.")

        return errors


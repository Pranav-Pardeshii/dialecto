from app.core.config import get_settings


def test_settings_load() -> None:
    settings = get_settings()
    assert settings.PORT == 8000
    assert "openai/gpt-oss-120b" in settings.LLM_PRIMARY_MODEL
    assert len(settings.fallback_models_list) > 0
    assert len(settings.cors_origins_list) > 0

import time

from app.ai.llm.budget import TokenBudgetManager


def test_token_budget_initial_capacity() -> None:
    manager = TokenBudgetManager(default_tokens_per_minute=6000)
    status = manager.get_status("model-a")
    assert status["capacity"] == 6000
    assert status["available"] == 6000
    assert status["pct_remaining"] == 100.0


def test_token_budget_consume() -> None:
    manager = TokenBudgetManager(default_tokens_per_minute=6000)
    assert manager.can_consume("model-a", 2000)
    manager.consume("model-a", 2000)

    status = manager.get_status("model-a")
    assert status["available"] <= 4001
    assert status["available"] >= 3995


def test_token_budget_prevents_overdraft() -> None:
    manager = TokenBudgetManager(default_tokens_per_minute=1000)
    manager.consume("model-b", 1000)
    # Immediately check
    assert not manager.can_consume("model-b", 500)


def test_token_budget_refill() -> None:
    # 6000 tokens/min = 100 tokens/sec
    manager = TokenBudgetManager(default_tokens_per_minute=6000)
    manager.consume("model-c", 6000)
    assert not manager.can_consume("model-c", 100)

    # Sleep 0.05s -> approx 5 tokens refilled
    time.sleep(0.06)
    assert manager.get_status("model-c")["available"] > 0

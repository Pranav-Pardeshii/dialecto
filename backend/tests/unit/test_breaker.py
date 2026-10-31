import time

from app.ai.llm.breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_initial_state() -> None:
    breaker = CircuitBreaker("test-model", max_failures=3, reset_timeout_s=10.0)
    assert not breaker.is_open()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_circuit_breaker_trips_after_max_failures() -> None:
    breaker = CircuitBreaker("test-model", max_failures=2, reset_timeout_s=5.0)
    breaker.record_failure()
    assert not breaker.is_open()
    assert str(breaker.state) == CircuitState.CLOSED.value
    assert breaker.failure_count == 1

    breaker.record_failure()
    assert breaker.is_open()
    assert str(breaker.state) == CircuitState.OPEN.value
    assert breaker.failure_count == 2


def test_circuit_breaker_immediate_trip_on_rate_limit() -> None:
    breaker = CircuitBreaker("test-model", max_failures=5, reset_timeout_s=10.0)
    breaker.record_failure(retry_after_s=20.0)
    assert breaker.is_open()
    assert str(breaker.state) == CircuitState.OPEN.value


def test_circuit_breaker_half_open_transition() -> None:
    breaker = CircuitBreaker("test-model", max_failures=1, reset_timeout_s=0.05)
    breaker.record_failure()
    assert breaker.is_open()

    # Sleep past the reset timeout
    time.sleep(0.06)
    # is_open() should transition to HALF_OPEN and return False to allow probe
    assert not breaker.is_open()
    assert str(breaker.state) == CircuitState.HALF_OPEN.value

    # Success closes it
    breaker.record_success()
    assert str(breaker.state) == CircuitState.CLOSED.value
    assert not breaker.is_open()

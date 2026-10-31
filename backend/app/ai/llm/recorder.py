import asyncio
import datetime
from collections import deque
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.entities import LLMCall, LLMCallStatusEnum

logger = structlog.get_logger(__name__)


class AsyncLLMRecorder:
    """Non-blocking recorder for LLM telemetry, draining to Postgres llm_calls table."""

    def __init__(self, max_queue_size: int = 1000, max_ring_buffer: int = 100) -> None:
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max_queue_size)
        self.ring_buffer: deque[dict[str, Any]] = deque(maxlen=max_ring_buffer)
        self._worker_task: asyncio.Task[None] | None = None
        self._running = False

    def start(self) -> None:
        if not self._running:
            self._running = True
            try:
                self._worker_task = asyncio.create_task(self._drain_worker())
            except RuntimeError:
                # No running event loop yet (e.g. during script or unit test setup)
                pass

    async def flush(self) -> None:
        """Drains any remaining items in queue to Postgres."""
        batch: list[dict[str, Any]] = []
        while not self.queue.empty():
            try:
                batch.append(self.queue.get_nowait())
                self.queue.task_done()
            except Exception:
                break
        if batch:
            await self._persist_batch(batch)

    async def stop(self) -> None:
        self._running = False
        await self.flush()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    def record(self, call_data: dict[str, Any]) -> None:
        """Push a call telemetry record non-blockingly."""
        record_copy = dict(call_data)
        record_copy.setdefault("created_at", datetime.datetime.now(datetime.UTC))
        self.ring_buffer.append(record_copy)

        try:
            self.queue.put_nowait(record_copy)
        except asyncio.QueueFull:
            # Drop oldest record to maintain non-blocking behavior
            try:
                _ = self.queue.get_nowait()
                self.queue.put_nowait(record_copy)
            except Exception:
                pass

    async def _drain_worker(self) -> None:
        """Background worker draining batches into Postgres."""
        while self._running:
            batch: list[dict[str, Any]] = []
            try:
                # Wait for at least one item
                item = await asyncio.wait_for(self.queue.get(), timeout=2.0)
                batch.append(item)
                self.queue.task_done()

                # Drain remaining available items in queue up to 50
                while len(batch) < 50:
                    try:
                        batch.append(self.queue.get_nowait())
                        self.queue.task_done()
                    except asyncio.QueueEmpty:
                        break

                if batch:
                    await self._persist_batch(batch)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("llm_recorder_drain_error", error=str(exc))
                await asyncio.sleep(1.0)

    async def _persist_batch(self, batch: list[dict[str, Any]]) -> None:
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    for item in batch:
                        status_val = item.get("status", LLMCallStatusEnum.OK)
                        if isinstance(status_val, str):
                            try:
                                status_val = LLMCallStatusEnum(status_val)
                            except ValueError:
                                status_val = LLMCallStatusEnum.ERROR

                        db_call = LLMCall(
                            purpose=item["purpose"],
                            model=item["model"],
                            attempt_no=item.get("attempt_no", 1),
                            fallback_used=item.get("fallback_used", False),
                            latency_ms=int(item["latency_ms"]),
                            prompt_tokens=int(item.get("prompt_tokens", 0)),
                            completion_tokens=int(item.get("completion_tokens", 0)),
                            status=status_val,
                            error_class=item.get("error_class"),
                            created_at=item.get("created_at")
                            or datetime.datetime.now(datetime.UTC),
                        )
                        session.add(db_call)
        except Exception as exc:
            # We never let DB persistence errors break LLM calls or bubble up
            logger.warning("llm_recorder_persist_failed", error=str(exc), batch_len=len(batch))

    def get_recent_stats(self) -> dict[str, Any]:
        """Calculates fast in-memory telemetry from ring buffer."""
        items = list(self.ring_buffer)
        total_calls = len(items)
        if total_calls == 0:
            return {
                "total_calls": 0,
                "fallback_rate": 0.0,
                "error_rate": 0.0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "models": {},
                "recent_calls": [],
            }

        fallback_count = sum(1 for x in items if x.get("fallback_used"))
        error_count = sum(1 for x in items if x.get("status") != LLMCallStatusEnum.OK)
        latencies = sorted(int(x.get("latency_ms", 0)) for x in items)

        p50_idx = int(0.50 * (len(latencies) - 1))
        p95_idx = int(0.95 * (len(latencies) - 1))

        models_breakdown: dict[str, dict[str, Any]] = {}
        for x in items:
            m = x["model"]
            if m not in models_breakdown:
                models_breakdown[m] = {
                    "calls": 0,
                    "errors": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "latencies": [],
                }
            models_breakdown[m]["calls"] += 1
            if x.get("status") != LLMCallStatusEnum.OK:
                models_breakdown[m]["errors"] += 1
            models_breakdown[m]["prompt_tokens"] += int(x.get("prompt_tokens", 0))
            models_breakdown[m]["completion_tokens"] += int(x.get("completion_tokens", 0))
            models_breakdown[m]["latencies"].append(int(x.get("latency_ms", 0)))

        for m, stats in models_breakdown.items():
            lats = sorted(stats.pop("latencies"))
            stats["avg_latency_ms"] = round(sum(lats) / len(lats)) if lats else 0

        # Return latest 10 formatted calls for the table
        formatted_recent = []
        for x in reversed(items[-10:]):
            formatted_recent.append(
                {
                    "purpose": x["purpose"],
                    "model": x["model"],
                    "latency_ms": x["latency_ms"],
                    "status": str(x.get("status", "ok")),
                    "fallback_used": x.get("fallback_used", False),
                    "tokens": int(x.get("prompt_tokens", 0)) + int(x.get("completion_tokens", 0)),
                    "created_at": x.get("created_at").isoformat()
                    if hasattr(x.get("created_at"), "isoformat")
                    else str(x.get("created_at")),
                }
            )

        return {
            "total_calls": total_calls,
            "fallback_rate": round((fallback_count / total_calls) * 100, 1),
            "error_rate": round((error_count / total_calls) * 100, 1),
            "p50_latency_ms": latencies[p50_idx],
            "p95_latency_ms": latencies[p95_idx],
            "models": models_breakdown,
            "recent_calls": formatted_recent,
        }

    async def get_db_stats(self, session: AsyncSession) -> dict[str, Any]:
        """Calculates telemetry using persisted llm_calls table, falling back to ring buffer if empty."""
        try:
            stmt = select(LLMCall).order_by(LLMCall.created_at.desc()).limit(200)
            db_calls = (await session.execute(stmt)).scalars().all()
            if not db_calls:
                return self.get_recent_stats()

            total_calls = len(db_calls)
            fallback_count = sum(1 for c in db_calls if c.fallback_used)
            error_count = sum(1 for c in db_calls if c.status != LLMCallStatusEnum.OK)
            latencies = sorted(int(c.latency_ms) for c in db_calls)
            p50_idx = int(0.50 * (len(latencies) - 1))
            p95_idx = int(0.95 * (len(latencies) - 1))

            models_breakdown: dict[str, dict[str, Any]] = {}
            for c in db_calls:
                m = c.model
                if m not in models_breakdown:
                    models_breakdown[m] = {
                        "calls": 0,
                        "errors": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "latencies": [],
                    }
                models_breakdown[m]["calls"] += 1
                if c.status != LLMCallStatusEnum.OK:
                    models_breakdown[m]["errors"] += 1
                models_breakdown[m]["prompt_tokens"] += c.prompt_tokens
                models_breakdown[m]["completion_tokens"] += c.completion_tokens
                models_breakdown[m]["latencies"].append(c.latency_ms)

            for m, stats in models_breakdown.items():
                lats = sorted(stats.pop("latencies"))
                stats["avg_latency_ms"] = round(sum(lats) / len(lats)) if lats else 0

            formatted_recent = [
                {
                    "purpose": c.purpose,
                    "model": c.model,
                    "latency_ms": c.latency_ms,
                    "status": str(c.status.value if hasattr(c.status, "value") else c.status),
                    "fallback_used": c.fallback_used,
                    "tokens": c.prompt_tokens + c.completion_tokens,
                    "created_at": c.created_at.isoformat()
                    if hasattr(c.created_at, "isoformat")
                    else str(c.created_at),
                }
                for c in db_calls[:10]
            ]

            return {
                "total_calls": total_calls,
                "fallback_rate": round((fallback_count / total_calls) * 100, 1),
                "error_rate": round((error_count / total_calls) * 100, 1),
                "p50_latency_ms": latencies[p50_idx],
                "p95_latency_ms": latencies[p95_idx],
                "models": models_breakdown,
                "recent_calls": formatted_recent,
            }
        except Exception as exc:
            logger.warning("get_db_stats_fallback", error=str(exc))
            return self.get_recent_stats()


# Singleton recorder instance
recorder = AsyncLLMRecorder()

"""行程规划接口与 SSE 流式输出。

接口层只负责请求/响应和并发控制，真正的规划编排在服务层完成。
"""

from __future__ import annotations

import json
import queue
import threading
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.contracts import TripPlanCreateRequest
from app.services.store import plan_store
from app.services.trip_planner import create_trip_plan

router = APIRouter(prefix="/api")
_stream_semaphore = threading.BoundedSemaphore(get_settings().stream_max_concurrent)


def _save_if_success(result: dict) -> None:
    if result.get("status") == "success" and result.get("planId"):
        plan_store.save(result["planId"], result)


@router.post("/trip-plans")
def create_plan(request: TripPlanCreateRequest):
    result = create_trip_plan(request)
    _save_if_success(result)
    return result


@router.post("/trip-plans/stream")
async def create_plan_stream(request: Request, plan_request: TripPlanCreateRequest):
    settings = get_settings()
    acquired = _stream_semaphore.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=429, detail="Too many concurrent planning streams")

    event_queue: "queue.Queue[dict]" = queue.Queue(maxsize=settings.stream_queue_size)
    stop_event = threading.Event()

    def put_event(event: dict) -> None:
        if stop_event.is_set():
            return
        try:
            event_queue.put(event, timeout=1)
        except queue.Full:
            stop_event.set()

    def worker() -> None:
        try:
            result = create_trip_plan(
                plan_request,
                progress_callback=lambda event: put_event({"type": "progress", "payload": event}),
            )
            _save_if_success(result)
            put_event({"type": "final", "payload": result})
        except Exception as exc:  # noqa: BLE001
            put_event({"type": "error", "payload": {"message": str(exc)}})
        finally:
            put_event({"type": "done"})
            _stream_semaphore.release()

    threading.Thread(target=worker, daemon=True).start()

    async def event_stream():
        deadline = time.monotonic() + settings.stream_timeout_seconds
        last_heartbeat_at = time.monotonic()
        try:
            while True:
                if await request.is_disconnected():
                    stop_event.set()
                    break
                if time.monotonic() > deadline:
                    stop_event.set()
                    yield f"data: {json.dumps({'type': 'error', 'payload': {'message': '规划超时，请稍后重试'}}, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                    break
                try:
                    item = event_queue.get(timeout=0.5)
                except queue.Empty:
                    now = time.monotonic()
                    if settings.stream_heartbeat_seconds > 0 and now - last_heartbeat_at >= settings.stream_heartbeat_seconds:
                        yield f"data: {json.dumps({'type': 'heartbeat', 'payload': {'message': '还在规划，马上回来'}}, ensure_ascii=False)}\n\n"
                        last_heartbeat_at = now
                    continue
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                last_heartbeat_at = time.monotonic()
                if item["type"] == "done":
                    break
        finally:
            stop_event.set()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/trip-plans/{plan_id}")
def get_plan(plan_id: str):
    plan = plan_store.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Trip plan not found")
    return plan

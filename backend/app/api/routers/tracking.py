"""前端埋点接口。

当前用进程内存储记录曝光、点击和规划事件，后续可替换为真实埋点管道。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.contracts import TrackingEvent
from app.services.store import tracking_event_store

router = APIRouter(prefix="/api")


@router.post("/tracking")
def track(event: TrackingEvent):
    received = tracking_event_store.append(event.model_dump(by_alias=True))
    return {"ok": True, "received": received}

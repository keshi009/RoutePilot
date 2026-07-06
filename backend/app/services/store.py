"""进程内运行期存储。

一期只需要本地演示和接口联调：保存已生成计划、埋点事件。
"""

from __future__ import annotations

from threading import Lock
from typing import Dict, List, Optional


class InMemoryPlanStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._plans: Dict[str, dict] = {}

    def save(self, plan_id: str, plan: dict) -> None:
        with self._lock:
            self._plans[plan_id] = plan

    def get(self, plan_id: str) -> Optional[dict]:
        with self._lock:
            return self._plans.get(plan_id)


class InMemoryEventStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._events: List[dict] = []

    def append(self, event: dict) -> int:
        with self._lock:
            self._events.append(event)
            return len(self._events)


plan_store = InMemoryPlanStore()
tracking_event_store = InMemoryEventStore()

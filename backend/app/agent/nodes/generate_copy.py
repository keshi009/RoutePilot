"""Step 7：生成展示文案。

LLM 只负责在确定性路线事实内写文案；失败时退化为模板，保证主流程不挂。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.contracts import TripNode
from app.services.llm import generate_trip_copy


def _facts(state: Dict[str, Any]) -> Dict[str, Any]:
    nodes = state.get("ordered_nodes", [])
    anchor = next((n for n in nodes if n.get("type") == "order"), nodes[0] if nodes else {})
    return {
        "traceId": state.get("trace_id", ""),
        "targetWindow": (state.get("request") or {}).get("target_window", "nearest_weekend"),
        "user": {
            "city": (state.get("user") or {}).get("city", ""),
            "preferenceTags": (state.get("user") or {}).get("preferenceTags", []),
        },
        "weather": state.get("weather", {}),
        "timingNote": state.get("timing_note", ""),
        "anchor": {
            "entityId": anchor.get("entityId", ""),
            "name": anchor.get("name", ""),
            "plannedStartTime": anchor.get("plannedStartTime", ""),
            "plannedEndTime": anchor.get("plannedEndTime", ""),
        },
        "route": state.get("route", {}),
        "routeScore": state.get("route_score", {}),
        "nodes": [
            {
                "nodeId": n.get("nodeId", ""),
                "type": n.get("type", ""),
                "name": n.get("name", ""),
                "category": n.get("category", ""),
                "plannedStartTime": n.get("plannedStartTime", ""),
                "plannedEndTime": n.get("plannedEndTime", ""),
                "scoreNotes": (n.get("score") or {}).get("notes", []),
            }
            for n in nodes
        ],
    }


def _apply_copy(nodes: List[Dict[str, Any]], copy_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    copy_by_id = {item.get("nodeId"): item for item in copy_payload.get("nodeCopies", [])}
    updated = []
    for raw in nodes:
        node = TripNode.model_validate(raw)
        item = copy_by_id.get(node.node_id, {})
        node.title = str(item.get("title") or node.title or node.name)[:10]
        node.reason = str(item.get("reason") or node.reason or "路线顺路，适合今天安排")[:20]
        updated.append(node.model_dump(by_alias=True))
    return updated


def generate_copy(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("failure_code"):
        return {}

    nodes = state.get("ordered_nodes", [])
    if not nodes:
        return {"failure_code": "empty_route"}

    payload = generate_trip_copy(_facts(state))
    return {
        "copy": payload,
        "ordered_nodes": _apply_copy(nodes, payload),
    }

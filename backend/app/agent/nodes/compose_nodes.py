"""Step 5：组合行程节点。

以锚点订单为中心，组合"1 个订单节点 + N 个高分兴趣/POI 节点"，
保证 PRD 硬要求：至少 1 个待使用订单节点 + 1 个兴趣节点。
产出 composed_nodes（统一的节点描述，供 Step6 路线求解）。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.agent import constraints
from app.contracts import BusinessHours, Merchant, Order, Poi
from app.tools import get_tool

MAX_INTEREST_NODES = 4  # 订单锚点 + 最多 4 个兴趣 = 最多 5 节点


def _order_node(order: Order, merchant: Merchant, hours: BusinessHours, weekday: int) -> Dict[str, Any]:
    biz = constraints.business_day_window(hours, weekday)
    # 订单节点时间窗取"订单可用窗 ∩ 营业窗"的近似：用营业窗兜底。
    order_wins = constraints.order_time_windows_minutes(order)
    if order_wins and biz:
        lo = max(order_wins[0][0], biz[0])
        hi = min(order_wins[0][1], biz[1])
    elif biz:
        lo, hi = biz
    else:
        lo, hi = (600, 1200)
    return {
        "kind": "order",
        "ref_id": order.order_id,
        "type": "order",
        "name": order.title,
        "category": order.category,
        "location": merchant.location.model_dump(by_alias=True) if merchant else order.model_dump(by_alias=True).get("location", {}),
        "image_url": order.image_url,
        "time_window": [lo, hi],
        "service_minutes": 60,
        "value": order.value,
        "action_type": "use_order",
        "reservation_required": order.needs_reservation or (merchant.reservation_required if merchant else False),
    }


def _poi_node(candidate: Dict[str, Any]) -> Dict[str, Any]:
    poi = Poi.model_validate(candidate["poi"])
    lo, hi = constraints.node_time_window(poi.open_time, poi.close_time)
    node_type = poi.source if poi.source in ("interest", "hotspot", "nearby") else "interest"
    return {
        "kind": "poi",
        "ref_id": poi.poi_id,
        "type": node_type,
        "name": poi.name,
        "category": poi.category,
        "location": poi.location.model_dump(by_alias=True),
        "image_url": poi.image_url,
        "time_window": [lo, hi],
        "service_minutes": 45,
        "value": poi.avg_price,
        "action_type": poi.action_type,
        "score": candidate.get("score", {}),
        "reservation_required": False,
    }


def compose_nodes(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("failure_code"):
        return {}

    request = state.get("request", {})
    weekday = int(request.get("weekday", 5))
    trace_id = state.get("trace_id", "")
    anchor_id = state.get("anchor_order_id", "")
    orders = {o["orderId"]: Order.model_validate(o) for o in state.get("orders", [])}
    anchor_order = orders.get(anchor_id)

    if not anchor_order:
        return {"failure_code": "no_anchor_selected"}

    merchant_res = get_tool("fetch_merchant_info").invoke(
        {"merchant_id": anchor_order.merchant_id, "trace_id": trace_id}
    )
    data = merchant_res.get("data") or {}
    merchant = Merchant.model_validate(data["merchant"]) if data.get("merchant") else None
    hours = BusinessHours.model_validate(data["business_hours"]) if data.get("business_hours") else None

    composed: List[Dict[str, Any]] = [_order_node(anchor_order, merchant, hours, weekday)]

    # 追加高分兴趣/POI 节点（已按分排序）。
    for cand in state.get("candidate_nodes", [])[:MAX_INTEREST_NODES]:
        composed.append(_poi_node(cand))

    interest_count = sum(1 for n in composed if n["kind"] == "poi")
    update: Dict[str, Any] = {"composed_nodes": composed}
    if interest_count < 1:
        # PRD 硬要求：至少 1 订单 + 1 兴趣，否则失败。
        update["failure_code"] = "insufficient_nodes"
    return update

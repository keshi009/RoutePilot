"""Step 1：识别用户可规划资产（待使用订单、兴趣信号）。"""

from __future__ import annotations

from typing import Any, Dict

from app.tools import get_tool


def identify_assets(state: Dict[str, Any]) -> Dict[str, Any]:
    request = state.get("request", {})
    user_id = request.get("user_id", "u_mock_001")
    scenario = request.get("scenario")
    trace_id = state.get("trace_id", "")

    user_res = get_tool("fetch_user_profile").invoke({"user_id": user_id, "trace_id": trace_id})
    orders_res = get_tool("fetch_unused_orders").invoke(
        {"user_id": user_id, "scenario": scenario, "trace_id": trace_id}
    )
    interests_res = get_tool("fetch_interest_signals").invoke({"user_id": user_id, "trace_id": trace_id})

    user = (user_res.get("data") or {}).get("user") or {}
    orders = (orders_res.get("data") or {}).get("orders") or []
    interests = (interests_res.get("data") or {}).get("interests") or []

    update: Dict[str, Any] = {
        "user": user,
        "orders": orders,
        "interests": interests,
    }
    if not orders:
        update["failure_code"] = "no_eligible_orders"
    return update

"""Step 2：判断是否存在适合出行的时机（订单可用性 + 天气）。

确定性判断每个订单今天是否可用（时间窗×营业时段×商家状态）。无任一可用订单则失败。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.agent import constraints
from app.contracts import BusinessHours, Merchant, Order
from app.tools import get_tool


def judge_timing(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("failure_code"):
        return {}

    request = state.get("request", {})
    weekday = int(request.get("weekday", 5))  # 默认周六
    trace_id = state.get("trace_id", "")
    user = state.get("user", {})
    orders_raw = state.get("orders", [])

    availability: Dict[str, Any] = {}
    usable_ids: List[str] = []

    for od in orders_raw:
        order = Order.model_validate(od)
        merchant_res = get_tool("fetch_merchant_info").invoke(
            {"merchant_id": order.merchant_id, "trace_id": trace_id}
        )
        data = merchant_res.get("data") or {}
        merchant = Merchant.model_validate(data["merchant"]) if data.get("merchant") else None
        hours = BusinessHours.model_validate(data["business_hours"]) if data.get("business_hours") else None

        usable, warnings = constraints.is_order_usable_today(order, merchant, hours, weekday)
        availability[order.order_id] = {"usable": usable, "warnings": warnings}
        if usable:
            usable_ids.append(order.order_id)

    weather_res = get_tool("fetch_weather").invoke(
        {"city": user.get("city", ""), "date": request.get("target_window", "nearest_weekend"), "trace_id": trace_id}
    )
    weather = (weather_res.get("data") or {}).get("weather") or {}

    update: Dict[str, Any] = {
        "order_availability": availability,
        "usable_order_ids": usable_ids,
        "weather": weather,
        "timing_note": f"今日可用订单 {len(usable_ids)} 张",
    }
    if not usable_ids:
        update["failure_code"] = "no_usable_time"
    return update

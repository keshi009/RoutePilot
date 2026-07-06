"""Step 4：选择主锚点订单（score_anchor 打分取最高）。"""

from __future__ import annotations

from typing import Any, Dict

from app.agent import scoring
from app.contracts import Merchant, Order, UserProfile
from app.tools import get_tool


def select_anchor(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("failure_code"):
        return {}

    trace_id = state.get("trace_id", "")
    user = UserProfile.model_validate(state.get("user", {}))
    usable_ids = set(state.get("usable_order_ids", []))
    orders = [Order.model_validate(o) for o in state.get("orders", [])]
    nearby_interest_count = len(state.get("candidate_nodes", []))

    best_id = ""
    best_score = None
    best_total = float("-inf")
    score_candidates = []

    for order in orders:
        if order.order_id not in usable_ids:
            continue
        merchant_res = get_tool("fetch_merchant_info").invoke(
            {"merchant_id": order.merchant_id, "trace_id": trace_id}
        )
        data = merchant_res.get("data") or {}
        merchant = Merchant.model_validate(data["merchant"]) if data.get("merchant") else None
        sb = scoring.score_anchor(
            order=order, merchant=merchant, user=user,
            usable_today=True, nearby_interest_count=nearby_interest_count,
        )
        score_candidates.append({
            "order_id": order.order_id,
            "title": order.title,
            "merchant_id": order.merchant_id,
            "score": sb.model_dump(),
        })
        if sb.total > best_total:
            best_total = sb.total
            best_id = order.order_id
            best_score = sb

    update: Dict[str, Any] = {
        "anchor_order_id": best_id,
        "anchor_score_candidates": score_candidates,
    }
    if best_score is not None:
        update["anchor_score"] = best_score.model_dump()
    if not best_id:
        update["failure_code"] = "no_anchor_selected"
    return update

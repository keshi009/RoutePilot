"""Step 3：召回候选目的地（周边 POI / 兴趣 / 热点），并用 score_node 打分。

产出 candidate_nodes：每个含 poi 原始数据 + 打分明细，作为后续 OPTW 的 profit 来源。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.agent import constraints, scoring
from app.agent.geo import haversine_meters
from app.contracts import InterestSignal, Location, Poi, UserProfile
from app.tools import get_tool

# 召回半径（米）：超出视为不顺路，Step3 先粗过滤。
RECALL_RADIUS_M = 12000


def recall_candidates(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("failure_code"):
        return {}

    request = state.get("request", {})
    scenario = request.get("scenario")
    trace_id = state.get("trace_id", "")
    user = UserProfile.model_validate(state.get("user", {}))
    interests = [InterestSignal.model_validate(i) for i in state.get("interests", [])]

    loc = user.current_location
    pois_res = get_tool("fetch_nearby_pois").invoke({
        "lat": loc.lat, "lng": loc.lng, "radius_m": RECALL_RADIUS_M,
        "scenario": scenario, "trace_id": trace_id,
    })
    pois = [Poi.model_validate(p) for p in (pois_res.get("data") or {}).get("pois", [])]

    # 过滤异常 POI + 超半径。
    pois = constraints.filter_recommendable(pois)
    candidates: List[Dict[str, Any]] = []
    for poi in pois:
        dist = haversine_meters(loc, poi.location)
        if dist > RECALL_RADIUS_M:
            continue
        sb = scoring.score_node(
            node_location=poi.location,
            tags=poi.recommended_tags + [poi.category],
            user=user,
            interests=interests,
            heat=poi.heat,
            rating=poi.rating,
            value=poi.avg_price,
            anchor_location=loc,
            risk=0.0,
        )
        candidates.append({
            "poi": poi.model_dump(by_alias=True),
            "score": sb.model_dump(),
            "distance_m": int(dist),
        })

    candidates.sort(key=lambda c: c["score"]["total"], reverse=True)
    update: Dict[str, Any] = {"candidate_nodes": candidates}
    if not candidates:
        # 无兴趣候选也允许继续（后面 compose 会判断能否满足最少节点），先记录。
        update["timing_note"] = state.get("timing_note", "") + "；无可用兴趣候选"
    return update

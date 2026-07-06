"""Step 6：路线规划与排序（OPTW 求解 + 硬约束校验）。

- 把 composed_nodes 转成 SolveNode（起点=用户位置，锚点订单 mandatory）。
- profit 用节点分数 ×1000 放大成整数，确保 profit 主导弧成本（否则 OR-Tools 会 drop 掉低收益点）。
- 调 solve_optw（OR-Tools 主 + 启发式兜底）。
- 生成 RouteSummary + ordered_nodes（TripNode dict）+ route_score。
- validate_route 校验硬约束，超限 -> failure_code。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.agent import constraints, scoring
from app.agent.geo import haversine_meters, meters_to_minutes
from app.agent.route_solver import SolveNode, solve_optw
from app.contracts import (
    Availability,
    Location,
    RouteSegment,
    RouteSummary,
    ScoreBreakdown,
    TripAction,
    TripNode,
    UserProfile,
)

PROFIT_SCALE = 1000  # 分数→整数 profit 放大系数


def _action_for(node: Dict[str, Any]) -> TripAction:
    at = node.get("action_type", "view")
    if node["kind"] == "order":
        return TripAction(type="use_order", label="去使用", enabled=True)
    label = {"view": "查看", "browse": "去逛逛", "purchase_placeholder": "去购买"}.get(at, "查看")
    return TripAction(type=at if at in ("view", "browse", "purchase_placeholder") else "view",
                      label=label, enabled=True)


def plan_route(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("failure_code"):
        return {}

    request = state.get("request", {})
    start_minute = int(request.get("start_minute", 630))  # 默认 10:30 出发
    user = UserProfile.model_validate(state.get("user", {}))
    composed = state.get("composed_nodes", [])
    anchor_id = state.get("anchor_order_id", "")

    # 起点 + 各候选节点。
    origin_loc = user.current_location
    locations: List[Location] = [origin_loc]
    solve_nodes: List[SolveNode] = [SolveNode("origin", 0, (0, 24 * 60 - 1), 0, False)]

    for node in composed:
        loc = Location.model_validate(node["location"])
        locations.append(loc)
        score_total = (node.get("score", {}) or {}).get("total", 0.5)
        # 订单锚点给高基础 profit，确保必达且价值突出。
        profit = int(max(0.05, score_total) * PROFIT_SCALE)
        if node["kind"] == "order":
            profit = max(profit, int(0.8 * PROFIT_SCALE))
        tw = node.get("time_window", [0, 24 * 60 - 1])
        solve_nodes.append(SolveNode(
            ref_id=node["ref_id"], profit=profit,
            time_window=(int(tw[0]), int(tw[1])),
            service_minutes=int(node.get("service_minutes", 45)),
            mandatory=(node["ref_id"] == anchor_id),
        ))

    from app.agent.geo import build_time_matrix
    time_matrix = build_time_matrix(locations)

    result = solve_optw(
        solve_nodes, time_matrix,
        budget_minutes=constraints.MAX_TOTAL_MINUTES,
        max_stops=constraints.MAX_NODES,
        start_minute=start_minute,
    )

    # 组装有序 TripNode（跳过起点 index 0）。
    node_by_ref = {n["ref_id"]: n for n in composed}
    ordered_trip_nodes: List[Dict[str, Any]] = []
    segments: List[RouteSegment] = []
    polyline: List[Location] = [origin_loc]
    total_distance = 0
    prev_idx = 0

    visited = [i for i in result.ordered_indices if i != 0]
    for seq, idx in enumerate(visited):
        sn = solve_nodes[idx]
        node = node_by_ref.get(sn.ref_id)
        if not node:
            continue
        loc = locations[idx]
        dist = int(haversine_meters(locations[prev_idx], loc))
        dur = meters_to_minutes(dist)
        total_distance += dist
        arrival = result.arrival_minutes[result.ordered_indices.index(idx)] if idx in result.ordered_indices else start_minute
        end_time = arrival + sn.service_minutes

        segments.append(RouteSegment(
            from_node_id=("origin" if prev_idx == 0 else solve_nodes[prev_idx].ref_id),
            to_node_id=sn.ref_id, distance_meters=dist, duration_minutes=dur,
            polyline=[locations[prev_idx], loc],
        ))
        polyline.append(loc)

        ordered_trip_nodes.append(TripNode(
            node_id=f"node_{seq+1}",
            type=node["type"],
            title=node["name"],                 # 文案节点会覆盖 title
            reason="",
            entity_id=sn.ref_id,
            name=node["name"],
            category=node.get("category", ""),
            location=loc,
            image_url=node.get("image_url", ""),
            planned_start_time=constraints.minutes_to_hhmm(arrival),
            planned_end_time=constraints.minutes_to_hhmm(end_time),
            distance_from_previous_meters=dist,
            duration_from_previous_minutes=dur,
            action=_action_for(node),
            availability=Availability(is_open=True, is_order_usable=(node["kind"] == "order")),
            score=ScoreBreakdown.model_validate(node.get("score", {})) if node.get("score") else ScoreBreakdown(),
        ).model_dump(by_alias=True))
        prev_idx = idx

    node_count = len(ordered_trip_nodes)
    total_minutes = (result.arrival_minutes[-1] + solve_nodes[visited[-1]].service_minutes - start_minute) if visited else 0

    checks = constraints.validate_route(node_count, total_minutes)
    interest_nodes = sum(1 for n in ordered_trip_nodes if n["type"] != "order")
    route_score = scoring.score_route(
        node_count=node_count, total_minutes=total_minutes,
        interest_node_count=interest_nodes, anchor_usable=True,
        purchase_node_count=sum(1 for n in composed if n.get("action_type") == "purchase_placeholder"),
    )

    route = RouteSummary(
        total_distance_meters=total_distance,
        total_duration_minutes=total_minutes,
        polyline=polyline, segments=segments,
    ).model_dump(by_alias=True)

    update: Dict[str, Any] = {
        "ordered_nodes": ordered_trip_nodes,
        "route": route,
        "route_score": route_score.model_dump(),
        "route_engine": result.engine,
        "rule_checks": [c.model_dump(by_alias=True) for c in checks],
    }
    if constraints.has_blocking(checks) or not result.feasible or node_count < constraints.MIN_NODES:
        update["failure_code"] = "route_constraint_violated"
    return update

"""汇总节点：把工作流状态组装为 TripPlan 或 PlanningFailure。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.agent import constraints
from app.contracts import (
    Location,
    PlanningFailure,
    RouteSummary,
    RuleCheck,
    ScoreBreakdown,
    TimeWindow,
    TripNode,
    TripPlan,
    TripSummary,
    UserProfile,
)


FAILURE_MESSAGES = {
    "no_eligible_orders": "当前没有可用于规划的待使用订单。",
    "no_usable_time": "最近周末没有时间可用且门店营业的订单。",
    "no_anchor_selected": "没有找到适合作为路线锚点的订单。",
    "insufficient_nodes": "附近缺少可组合的兴趣节点，暂时无法生成路线。",
    "route_constraint_violated": "候选路线未通过节点数、时间窗或 5 小时约束。",
    "empty_route": "路线节点为空，暂时无法生成行程。",
}


def _plan_id(trace_id: str) -> str:
    return f"plan_{trace_id[-12:]}" if trace_id else "plan_unknown"


def _rule_checks(raw: List[Dict[str, Any]]) -> List[RuleCheck]:
    return [RuleCheck.model_validate(item) for item in raw or []]


def _debug(state: Dict[str, Any]) -> Dict[str, Any]:
    request = state.get("request") or {}
    if not request.get("include_debug"):
        return {}
    return {
        "routeEngine": state.get("route_engine", ""),
        "anchorScore": state.get("anchor_score", {}),
        "routeScore": state.get("route_score", {}),
        "orderAvailability": state.get("order_availability", {}),
        "candidateNodeCount": len(state.get("candidate_nodes", [])),
        "composedNodeCount": len(state.get("composed_nodes", [])),
        "copy": state.get("copy", {}),
    }


def _time_window(state: Dict[str, Any]) -> TimeWindow:
    start_minute = int((state.get("request") or {}).get("start_minute", 630))
    return TimeWindow(
        start=constraints.minutes_to_hhmm(start_minute),
        end=constraints.minutes_to_hhmm(start_minute + constraints.MAX_TOTAL_MINUTES),
    )


def assemble(state: Dict[str, Any]) -> Dict[str, Any]:
    trace_id = state.get("trace_id", "")
    plan_id = _plan_id(trace_id)
    checks = _rule_checks(state.get("rule_checks", []))
    failure_code = state.get("failure_code", "")

    if failure_code:
        failure = PlanningFailure(
            plan_id=plan_id,
            trace_id=trace_id,
            failure_code=failure_code,
            message=FAILURE_MESSAGES.get(failure_code, "当前条件暂时无法生成可执行行程。"),
            rule_checks=checks,
            debug=_debug(state),
        )
        return {"trip_plan": failure.model_dump(by_alias=True)}

    user = UserProfile.model_validate(state.get("user", {}))
    copy_payload = state.get("copy", {})
    route_score = ScoreBreakdown.model_validate(state.get("route_score", {}))
    nodes = [TripNode.model_validate(item) for item in state.get("ordered_nodes", [])]
    route = RouteSummary.model_validate(state.get("route", {}))

    summary = TripSummary(
        title=copy_payload.get("summaryTitle", "最近周末推荐路线"),
        text=copy_payload.get("summaryText", "先用待使用订单，再顺路安排兴趣点，整体不超过五小时。"),
        entry_copy=copy_payload.get("entryCopy", "帮你把待使用订单串成顺路周末行程"),
        highlights=route_score.notes,
        llm_provider=copy_payload.get("llmProvider", "fallback"),
    )

    plan = TripPlan(
        plan_id=plan_id,
        trace_id=trace_id,
        target_date_label="最近周末",
        time_window=_time_window(state),
        user_location=Location.model_validate(user.current_location),
        summary=summary,
        anchor_order_id=state.get("anchor_order_id", ""),
        nodes=nodes,
        route=route,
        score=route_score,
        rule_checks=checks,
        debug=_debug(state),
    )
    return {"trip_plan": plan.model_dump(by_alias=True)}

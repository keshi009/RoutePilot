"""TripPlanner 服务：生成 trace_id，驱动 LangGraph，返回对外契约。

这里同时承担规划过程日志的统一出口：每个工作流节点完成后都会抽取关键中间态，
写入 trace JSONL 与 runtime JSONL，方便后续排查、评测和回放。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from loguru import logger

from app.agent.graph import TRIP_PLAN_GRAPH
from app.agent.trace import TripTrace
from app.contracts import EntryResponse, RuleCheck, TripPlanCreateRequest
from app.mock import fixtures
from app.agent import constraints

ProgressCallback = Callable[[Dict[str, Any]], None]


STEP_META = {
    "identify_assets": ("识别可规划资产", "读取待使用订单、用户位置和兴趣信号"),
    "judge_timing": ("判断可用时机", "校验订单可用时间、门店营业和天气"),
    "recall_candidates": ("召回兴趣节点", "查找附近 POI、热点和可顺路目的地"),
    "select_anchor": ("选择主锚点订单", "用规则得分选择最值得优先使用的订单"),
    "compose_nodes": ("组合行程节点", "把订单和兴趣点组合成候选路线节点"),
    "plan_route": ("优化路线排序", "使用 OPTW/OR-Tools 求解节点选择和顺序"),
    "generate_copy": ("生成展示文案", "在已验证路线事实内生成推荐理由"),
    "assemble": ("汇总规划结果", "输出前端可渲染的行程结构"),
}


def _progress_event(trace_id: str, sequence: int, step: str, update: Dict[str, Any]) -> Dict[str, Any]:
    title, detail = STEP_META.get(step, (step, ""))
    if update.get("failure_code"):
        detail = f"{detail}；失败码 {update['failure_code']}"
    return {
        "traceId": trace_id,
        "sequence": sequence,
        "time": datetime.now(timezone.utc).isoformat(),
        "eventType": step,
        "progressTitle": title,
        "detailText": detail,
    }


def _merge_state(state: Dict[str, Any], update: Dict[str, Any]) -> None:
    for key, value in update.items():
        if key == "rule_checks":
            state.setdefault("rule_checks", [])
            state["rule_checks"].extend(value or [])
        else:
            state[key] = value


def _pick(item: Dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return default


def _score_snapshot(score: Any) -> Dict[str, Any]:
    if not isinstance(score, dict):
        return {}
    return {
        "total": round(float(score.get("total", 0.0) or 0.0), 4),
        "factors": score.get("factors", {}),
        "penalties": score.get("penalties", {}),
        "notes": score.get("notes", []),
    }


def _order_summary(order: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "order_id": _pick(order, "orderId", "order_id"),
        "title": _pick(order, "title"),
        "merchant_id": _pick(order, "merchantId", "merchant_id"),
        "category": _pick(order, "category"),
        "status": _pick(order, "status"),
        "value": _pick(order, "value", default=0),
    }


def _candidate_summary(candidate: Dict[str, Any]) -> Dict[str, Any]:
    poi = candidate.get("poi") or {}
    score = _score_snapshot(candidate.get("score") or {})
    return {
        "poi_id": _pick(poi, "poiId", "poi_id"),
        "name": _pick(poi, "name"),
        "category": _pick(poi, "category"),
        "source": _pick(poi, "source"),
        "distance_m": candidate.get("distance_m", 0),
        "score_total": score.get("total", 0.0),
        "score": score,
    }


def _node_summary(node: Dict[str, Any]) -> Dict[str, Any]:
    score = node.get("score") or {}
    score_snapshot = _score_snapshot(score)
    return {
        "id": _pick(node, "ref_id", "refId", "entityId", "nodeId"),
        "kind": _pick(node, "kind", default=_pick(node, "type")),
        "type": _pick(node, "type"),
        "name": _pick(node, "name", "title"),
        "time_window": node.get("time_window", []),
        "planned_start": _pick(node, "plannedStartTime", "planned_start_time"),
        "planned_end": _pick(node, "plannedEndTime", "planned_end_time"),
        "score_total": score_snapshot.get("total", 0.0),
        "score": score_snapshot,
    }


def _rule_summary(rule: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rule_id": _pick(rule, "ruleId", "rule_id"),
        "passed": bool(rule.get("passed", True)),
        "severity": _pick(rule, "severity"),
        "message": _pick(rule, "message"),
        "affected_entity_id": _pick(rule, "affectedEntityId", "affected_entity_id"),
    }


def _route_summary(route: Any) -> Dict[str, Any]:
    if not isinstance(route, dict):
        return {}
    return {
        "total_distance_meters": _pick(route, "totalDistanceMeters", "total_distance_meters", default=0),
        "total_duration_minutes": _pick(route, "totalDurationMinutes", "total_duration_minutes", default=0),
        "segment_count": len(route.get("segments") or []),
        "polyline_points": len(route.get("polyline") or []),
    }


def _trace_payload(update: Dict[str, Any], state: Dict[str, Any], sequence: int) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    payload["sequence"] = sequence
    payload["state_keys"] = sorted(k for k in state.keys() if k not in {"user", "orders", "candidate_nodes"})

    for key in (
        "failure_code",
        "anchor_order_id",
        "route_engine",
        "timing_note",
    ):
        if key in update:
            payload[key] = update[key]

    if "anchor_score" in update:
        payload["anchor_score"] = _score_snapshot(update.get("anchor_score") or {})

    if "anchor_score_candidates" in update:
        payload["anchor_score_candidates"] = [
            {
                "order_id": item.get("order_id", ""),
                "title": item.get("title", ""),
                "merchant_id": item.get("merchant_id", ""),
                "score": _score_snapshot(item.get("score") or {}),
            }
            for item in update.get("anchor_score_candidates") or []
        ]

    if "route_score" in update:
        payload["route_score"] = _score_snapshot(update.get("route_score") or {})

    if "orders" in update:
        orders = update.get("orders") or []
        payload["order_count"] = len(orders)
        payload["orders"] = [_order_summary(item) for item in orders]

    if "order_availability" in update:
        availability = update.get("order_availability") or {}
        payload["usable_order_ids"] = list(update.get("usable_order_ids") or [])
        payload["blocked_orders"] = [
            {"order_id": oid, "warnings": info.get("warnings", [])}
            for oid, info in availability.items()
            if not info.get("usable")
        ]
        if update.get("weather"):
            weather = update["weather"]
            payload["weather"] = {
                "condition": weather.get("condition", ""),
                "temperature": weather.get("temperature", ""),
                "outdoor_suitable": weather.get("outdoorSuitable", weather.get("outdoor_suitable", "")),
            }

    if "candidate_nodes" in update:
        candidates = update.get("candidate_nodes") or []
        payload["candidate_node_count"] = len(candidates)
        payload["top_candidate_nodes"] = [_candidate_summary(item) for item in candidates[:5]]

    if "composed_nodes" in update:
        composed = update.get("composed_nodes") or []
        payload["composed_node_count"] = len(composed)
        payload["composed_nodes"] = [_node_summary(item) for item in composed]

    if "ordered_nodes" in update:
        ordered = update.get("ordered_nodes") or []
        payload["ordered_node_count"] = len(ordered)
        payload["ordered_nodes"] = [_node_summary(item) for item in ordered]

    if "route" in update:
        payload["route"] = _route_summary(update.get("route") or {})

    if "rule_checks" in update:
        rules = update.get("rule_checks") or []
        payload["rule_check_count"] = len(rules)
        payload["rule_checks"] = [_rule_summary(item) for item in rules]
        payload["blocking_rule_checks"] = [
            _rule_summary(item) for item in rules
            if item.get("severity") == "blocking" or not item.get("passed", True)
        ]

    if "copy" in update:
        copy_payload = update.get("copy") or {}
        payload["copy"] = {
            "llm_provider": copy_payload.get("llmProvider", ""),
            "summary_title": copy_payload.get("summaryTitle", ""),
            "node_copy_count": len(copy_payload.get("nodeCopies") or []),
        }

    if "trip_plan" in update:
        plan = update["trip_plan"]
        payload["plan_status"] = plan.get("status")
        payload["plan_id"] = plan.get("planId", "")
        payload["failure_code"] = plan.get("failureCode", payload.get("failure_code", ""))
        payload["node_count"] = len(plan.get("nodes") or [])
        payload["summary_title"] = (plan.get("summary") or {}).get("title", "")

    return payload


def create_trip_plan(
    request: TripPlanCreateRequest,
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, Any]:
    trace_id = uuid.uuid4().hex
    trace = TripTrace(trace_id=trace_id, user_id=request.user_id, scenario=request.scenario)
    state: Dict[str, Any] = {
        "trace_id": trace_id,
        "request": {
            **request.model_dump(),
            "weekday": 5,
            "start_minute": constraints.parse_hhmm("10:30") or 630,
        },
        "rule_checks": [],
    }

    try:
        trace.add_event(
            "planner_start",
            status="running",
            user_id=request.user_id,
            scenario=request.scenario,
            target_window=request.target_window,
            include_debug=request.include_debug,
        )
        sequence = 1
        for chunk in TRIP_PLAN_GRAPH.stream(state, stream_mode="updates"):
            for step, update in chunk.items():
                if not isinstance(update, dict):
                    continue
                _merge_state(state, update)
                event = _progress_event(trace_id, sequence, step, update)
                trace_status = "blocked" if update.get("failure_code") else "success"
                trace.add_event(step, status=trace_status, **_trace_payload(update, state, sequence))
                if progress_callback:
                    progress_callback(event)
                sequence += 1

        result = state.get("trip_plan") or {
            "status": "failed",
            "traceId": trace_id,
            "failureCode": "planner_no_result",
            "message": "规划流程未产生结果。",
            "ruleChecks": [],
        }
    except Exception as exc:  # noqa: BLE001 - 服务边界兜底
        logger.exception(f"[trace_id={trace_id}] 规划运行异常: {exc}")
        trace.add_event("planner_runtime", status="error", error=str(exc))
        result = {
            "planId": f"plan_{trace_id[-12:]}",
            "traceId": trace_id,
            "status": "failed",
            "failureCode": "planner_runtime_error",
            "message": f"规划运行异常：{type(exc).__name__}",
            "ruleChecks": [],
            "debug": {"error": str(exc)} if request.include_debug else {},
        }

    status = result.get("status", "failed")
    trace.add_event(
        "planner_result",
        status=status,
        plan_id=result.get("planId", ""),
        failure_code=result.get("failureCode", ""),
        node_count=len(result.get("nodes") or []),
    )
    trace.set_result(status=status, failure_code=result.get("failureCode", ""), plan_id=result.get("planId", ""))
    trace_files = trace.flush()
    if trace_files:
        result["planningLogFile"] = trace_files["jsonl"]
        result["readablePlanningLogFile"] = trace_files["readable"]
    return result


def build_assistant_entry(user_id: str = "u_mock_001", scenario: Optional[str] = None) -> Dict[str, Any]:
    user = fixtures.get_user(user_id)
    orders = fixtures.get_unused_orders(user_id, scenario)
    pois = constraints.filter_recommendable(fixtures.get_nearby_pois(
        user.current_location.lat,
        user.current_location.lng,
        scenario=scenario,
    ))

    checks = []
    candidate_ids = []
    for order in orders:
        merchant = fixtures.get_merchant(order.merchant_id)
        hours = fixtures.get_business_hours(order.merchant_id)
        usable, warnings = constraints.is_order_usable_today(order, merchant, hours, weekday=5)
        checks.append(RuleCheck(
            rule_id="entry_order_usable",
            passed=usable,
            severity="info" if usable else "warning",
            message=f"{order.title}: {'可规划' if usable else '暂不适合'}" + (f"（{';'.join(warnings)}）" if warnings else ""),
            affected_entity_id=order.order_id,
        ))
        if usable:
            candidate_ids.append(order.order_id)

    executable_count = len(candidate_ids) if pois else 0
    visible = executable_count > 0
    entry = EntryResponse(
        visible=visible,
        title="AI 订单助手" if visible else "暂无可推荐行程",
        subtitle="帮你把待使用订单安排成路线" if visible else "待使用订单还不适合出行",
        copy=(
            f"最近周末有 {len(candidate_ids)} 张订单适合安排，可以顺路串成一条路线"
            if visible else
            "最近周末暂时没有适合安排的路线"
        ),
        entry_copy_source="rules_precheck" if visible else "hidden",
        eligible_order_count=len(candidate_ids),
        total_unused_order_count=len(orders),
        executable_route_count=executable_count,
        candidate_order_ids=candidate_ids,
        reason_codes=["HAS_EXECUTABLE_WEEKEND_ROUTE"] if visible else ["NO_EXECUTABLE_WEEKEND_ROUTE"],
        rule_checks=checks,
    )
    if not orders:
        entry.reason_codes.append("NO_UNUSED_ORDER")
    return entry.model_dump(by_alias=True)

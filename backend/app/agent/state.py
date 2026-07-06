"""LangGraph 工作流状态。

固定 7 步工作流的共享状态。累积字段用 operator.add reducer，单值字段直接覆盖。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, TypedDict


class TripPlanState(TypedDict, total=False):
    trace_id: str
    request: Dict[str, Any]           # user_id, target_window, scenario, include_debug, weekday, start_minute

    # Step1 识别资产
    user: Dict[str, Any]
    orders: List[Dict[str, Any]]
    interests: List[Dict[str, Any]]

    # Step2 判断时机
    order_availability: Dict[str, Any]   # order_id -> {usable, warnings}
    usable_order_ids: List[str]
    weather: Dict[str, Any]
    timing_note: str

    # Step3 召回候选
    candidate_nodes: List[Dict[str, Any]]   # 兴趣/POI/热点候选（已打分）

    # Step4 主锚点
    anchor_order_id: str
    anchor_score: Dict[str, Any]
    anchor_score_candidates: List[Dict[str, Any]]

    # Step5 组合节点
    composed_nodes: List[Dict[str, Any]]

    # Step6 路线
    ordered_nodes: List[Dict[str, Any]]
    route: Dict[str, Any]
    route_score: Dict[str, Any]
    route_engine: str

    # Step7 文案
    copy: Dict[str, Any]

    # 汇总
    rule_checks: Annotated[List[Dict[str, Any]], operator.add]
    failure_code: str
    trip_plan: Dict[str, Any]

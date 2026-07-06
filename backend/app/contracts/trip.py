"""行程输出契约：节点、路线、概述、TripPlan / PlanningFailure。

这是对外 API 的核心返回结构，字段与前端 camelCase 契约保持一致。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import Location, ScoreBreakdown, RuleCheck, TimeWindow


class TripAction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal[
        "use_order", "reservation_hint", "view", "browse", "purchase_placeholder", "ai_followup"
    ] = "view"
    label: str = ""
    enabled: bool = True
    disabled_reason: Optional[str] = Field(default=None, alias="disabledReason")


class Availability(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_open: bool = Field(default=True, alias="isOpen")
    is_order_usable: bool = Field(default=True, alias="isOrderUsable")
    warnings: List[str] = Field(default_factory=list)


class TripNode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    node_id: str = Field(default="", alias="nodeId")
    type: Literal["order", "interest", "hotspot", "nearby"] = "order"
    title: str = ""
    reason: str = ""
    entity_id: str = Field(default="", alias="entityId")
    name: str = ""
    category: str = ""
    location: Location = Field(default_factory=Location)
    image_url: str = Field(default="", alias="imageUrl")
    planned_start_time: str = Field(default="", alias="plannedStartTime")
    planned_end_time: str = Field(default="", alias="plannedEndTime")
    distance_from_previous_meters: int = Field(default=0, alias="distanceFromPreviousMeters")
    duration_from_previous_minutes: int = Field(default=0, alias="durationFromPreviousMinutes")
    action: TripAction = Field(default_factory=TripAction)
    availability: Availability = Field(default_factory=Availability)
    score: ScoreBreakdown = Field(default_factory=ScoreBreakdown)


class RouteSegment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_node_id: str = Field(default="", alias="fromNodeId")
    to_node_id: str = Field(default="", alias="toNodeId")
    distance_meters: int = Field(default=0, alias="distanceMeters")
    duration_minutes: int = Field(default=0, alias="durationMinutes")
    polyline: List[Location] = Field(default_factory=list)


class RouteSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_distance_meters: int = Field(default=0, alias="totalDistanceMeters")
    total_duration_minutes: int = Field(default=0, alias="totalDurationMinutes")
    polyline: List[Location] = Field(default_factory=list)
    segments: List[RouteSegment] = Field(default_factory=list)


class TripSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = ""
    text: str = ""
    entry_copy: str = Field(default="", alias="entryCopy")
    highlights: List[str] = Field(default_factory=list)
    llm_provider: str = Field(default="", alias="llmProvider")


class TripPlan(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plan_id: str = Field(default="", alias="planId")
    trace_id: str = Field(default="", alias="traceId")
    status: Literal["success"] = "success"
    target_date_label: str = Field(default="", alias="targetDateLabel")
    time_window: TimeWindow = Field(default_factory=TimeWindow, alias="timeWindow")
    user_location: Location = Field(default_factory=Location, alias="userLocation")
    summary: TripSummary = Field(default_factory=TripSummary)
    anchor_order_id: str = Field(default="", alias="anchorOrderId")
    nodes: List[TripNode] = Field(default_factory=list)
    route: RouteSummary = Field(default_factory=RouteSummary)
    score: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    rule_checks: List[RuleCheck] = Field(default_factory=list, alias="ruleChecks")
    debug: Dict[str, Any] = Field(default_factory=dict)


class PlanningFailure(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plan_id: str = Field(default="", alias="planId")
    trace_id: str = Field(default="", alias="traceId")
    status: Literal["failed"] = "failed"
    failure_code: str = Field(default="", alias="failureCode")
    message: str = ""
    rule_checks: List[RuleCheck] = Field(default_factory=list, alias="ruleChecks")
    debug: Dict[str, Any] = Field(default_factory=dict)

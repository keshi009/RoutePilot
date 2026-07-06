"""API 请求/响应契约。"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import RuleCheck


class TripPlanCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(default="u_mock_001", alias="userId")
    target_window: Literal["nearest_weekend"] = Field(default="nearest_weekend", alias="targetWindow")
    include_debug: bool = Field(default=False, alias="includeDebug")
    scenario: Optional[str] = None


class EntryResponse(BaseModel):
    """订单列表页 AI 行程气泡入口 precheck 结果。"""

    model_config = ConfigDict(populate_by_name=True)

    visible: bool = False
    title: str = ""
    subtitle: str = ""
    entry_copy: str = Field(default="", alias="copy")
    entry_copy_source: Literal["rules_precheck", "hidden"] = Field(default="hidden", alias="entryCopySource")
    eligible_order_count: int = Field(default=0, alias="eligibleOrderCount")
    total_unused_order_count: int = Field(default=0, alias="totalUnusedOrderCount")
    executable_route_count: int = Field(default=0, alias="executableRouteCount")
    candidate_order_ids: List[str] = Field(default_factory=list, alias="candidateOrderIds")
    reason_codes: List[str] = Field(default_factory=list, alias="reasonCodes")
    rule_checks: List[RuleCheck] = Field(default_factory=list, alias="ruleChecks")
    data_mode: Literal["mock"] = Field(default="mock", alias="dataMode")


class TrackingEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_name: str = Field(default="", alias="eventName")
    user_id: str = Field(default="u_mock_001", alias="userId")
    plan_id: Optional[str] = Field(default=None, alias="planId")
    payload: Dict[str, Any] = Field(default_factory=dict)


class TripActionExecuteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plan_id: Optional[str] = Field(default=None, alias="planId")
    node_id: str = Field(default="", alias="nodeId")
    action_type: str = Field(default="", alias="actionType")
    entity_id: str = Field(default="", alias="entityId")
    user_id: str = Field(default="u_mock_001", alias="userId")


class TripActionExecuteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ok: bool = True
    status: Literal["recorded", "not_integrated"] = "not_integrated"
    message: str = ""
    next_step: Optional[str] = Field(default=None, alias="nextStep")

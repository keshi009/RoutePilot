"""统一数据契约层（Pydantic v2）。

所有 Agent 节点、工具、服务、API 共享这里的模型。集中导出，避免深层 import。
"""

from .common import Location, TimeWindow, ScoreBreakdown, RuleCheck
from .domain import (
    UserProfile,
    InterestSignal,
    BusinessDay,
    BusinessHours,
    Merchant,
    Order,
    Poi,
    WeatherSnapshot,
)
from .trip import (
    TripAction,
    Availability,
    TripNode,
    RouteSegment,
    RouteSummary,
    TripSummary,
    TripPlan,
    PlanningFailure,
)
from .tool_result import ToolResult
from .api import (
    EntryResponse,
    TrackingEvent,
    TripActionExecuteRequest,
    TripActionExecuteResponse,
    TripPlanCreateRequest,
)

__all__ = [
    # common
    "Location",
    "TimeWindow",
    "ScoreBreakdown",
    "RuleCheck",
    # domain
    "UserProfile",
    "InterestSignal",
    "BusinessDay",
    "BusinessHours",
    "Merchant",
    "Order",
    "Poi",
    "WeatherSnapshot",
    # trip
    "TripAction",
    "Availability",
    "TripNode",
    "RouteSegment",
    "RouteSummary",
    "TripSummary",
    "TripPlan",
    "PlanningFailure",
    # tool
    "ToolResult",
    # api
    "TripPlanCreateRequest",
    "EntryResponse",
    "TrackingEvent",
    "TripActionExecuteRequest",
    "TripActionExecuteResponse",
]

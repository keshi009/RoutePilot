"""规划失败路径测试。

用 mock scenario 验证无订单、周末不可用、无 POI 等条件会返回稳定失败码。
"""

from app.contracts import TripPlanCreateRequest
from app.services.trip_planner import create_trip_plan


def test_no_orders_failure():
    result = create_trip_plan(TripPlanCreateRequest(userId="u_mock_001", scenario="no_orders"))

    assert result["status"] == "failed"
    assert result["failureCode"] == "no_eligible_orders"


def test_weekend_unavailable_failure():
    result = create_trip_plan(TripPlanCreateRequest(userId="u_mock_001", scenario="weekend_unavailable"))

    assert result["status"] == "failed"
    assert result["failureCode"] == "no_usable_time"


def test_no_poi_failure():
    result = create_trip_plan(TripPlanCreateRequest(userId="u_mock_001", scenario="no_poi"))

    assert result["status"] == "failed"
    assert result["failureCode"] == "insufficient_nodes"

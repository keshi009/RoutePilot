"""规划成功路径测试。

验证主流程能产出 TripPlan、路线约束满足、trace 落盘且 route engine 可观测。
"""

from pathlib import Path

from app.contracts import TripPlanCreateRequest
from app.services.trip_planner import create_trip_plan


def test_create_trip_plan_success():
    result = create_trip_plan(TripPlanCreateRequest(userId="u_mock_001", includeDebug=True))

    assert result["status"] == "success"
    assert result["anchorOrderId"] in {"order_201", "order_202", "order_203", "order_204"}
    assert 2 <= len(result["nodes"]) <= 5
    assert any(node["type"] == "order" for node in result["nodes"])
    assert any(node["type"] != "order" for node in result["nodes"])
    assert result["route"]["totalDurationMinutes"] <= 300
    assert result["summary"]["llmProvider"] == "test-fake"
    assert result["planningLogFile"]
    assert result["readablePlanningLogFile"]

    trace_lines = Path(result["planningLogFile"]).read_text(encoding="utf-8").splitlines()
    assert any('"record": "event"' in line and '"step": "plan_route"' in line for line in trace_lines)
    assert any('"record": "result"' in line and '"status": "success"' in line for line in trace_lines)
    readable_log = Path(result["readablePlanningLogFile"]).read_text(encoding="utf-8")
    assert "路线评分拆解" in readable_log
    assert "硬规则约束校验" in readable_log
    assert result["debug"]["routeEngine"] in {"ortools", "heuristic"}

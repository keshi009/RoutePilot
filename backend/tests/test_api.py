"""后端 HTTP API 契约测试。

覆盖本期保留接口、已移除 health 接口、SSE 流式响应和动作/埋点基础返回。
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_api_is_not_registered():
    response = client.get("/api/health")

    assert response.status_code == 404


def test_create_trip_plan_api():
    response = client.post(
        "/api/trip-plans",
        json={"userId": "u_mock_001", "targetWindow": "nearest_weekend", "includeDebug": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["nodes"]
    assert body["route"]["totalDurationMinutes"] <= 300
    assert body["summary"]["llmProvider"] == "test-fake"
    assert body["planningLogFile"]
    assert body["readablePlanningLogFile"]


def test_create_trip_plan_stream_api():
    with client.stream(
        "POST",
        "/api/trip-plans/stream",
        json={"userId": "u_mock_001", "targetWindow": "nearest_weekend", "includeDebug": False},
    ) as response:
        assert response.status_code == 200
        payload = response.read().decode("utf-8")

    assert '"type": "progress"' in payload
    assert '"type": "final"' in payload
    assert '"status": "success"' in payload


def test_orders_api():
    response = client.get("/api/orders")

    assert response.status_code == 200
    assert any(order["status"] == "unused" for order in response.json())


def test_trip_assistant_entry_api():
    response = client.get("/api/trip-assistant/entry")

    assert response.status_code == 200
    body = response.json()
    assert body["visible"] is True
    assert body["eligibleOrderCount"] >= 1
    assert body["executableRouteCount"] >= 1
    assert body["candidateOrderIds"]
    assert "HAS_EXECUTABLE_WEEKEND_ROUTE" in body["reasonCodes"]


def test_trip_action_execute_api():
    response = client.post(
        "/api/trip-actions/execute",
        json={
            "planId": "plan_mock",
            "nodeId": "node_order_001",
            "actionType": "use_order",
            "entityId": "order_001",
            "userId": "u_mock_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "not_integrated"


def test_get_unknown_plan_does_not_regenerate():
    response = client.get("/api/trip-plans/not_exist")

    assert response.status_code == 404

"""订单列表页数据与 AI 助手入口。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.mock import fixtures
from app.services.trip_planner import build_assistant_entry

router = APIRouter(prefix="/api")


@router.get("/orders")
def list_orders(user_id: str = Query("u_mock_001", alias="userId"), scenario: str = Query(None)):
    return [order.model_dump(by_alias=True) for order in fixtures.get_unused_orders(user_id, scenario)]


@router.get("/orders/{order_id}")
def get_order(order_id: str, user_id: str = Query("u_mock_001", alias="userId")):
    for order in fixtures.get_unused_orders(user_id):
        if order.order_id == order_id:
            return order.model_dump(by_alias=True)
    raise HTTPException(status_code=404, detail="Order not found")


@router.get("/trip-assistant/entry")
def get_trip_assistant_entry(user_id: str = Query("u_mock_001", alias="userId"), scenario: str = Query(None)):
    return build_assistant_entry(user_id=user_id, scenario=scenario)

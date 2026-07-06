"""行程节点动作接口。

一期只记录按钮点击，不调用真实核销、预约、购买等履约 RPC。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.contracts import TripActionExecuteRequest, TripActionExecuteResponse
from app.services.store import tracking_event_store

router = APIRouter(prefix="/api")


@router.post("/trip-actions/execute")
def execute_trip_action(action: TripActionExecuteRequest):
    tracking_event_store.append({"eventName": "trip_action_execute", **action.model_dump(by_alias=True)})
    response = TripActionExecuteResponse(
        ok=True,
        status="not_integrated",
        message="本期先记录点击，真实履约动作后续接订单/RPC。",
        next_step="recorded_for_eval",
    )
    return response.model_dump(by_alias=True)

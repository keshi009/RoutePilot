"""RoutePilot API 路由聚合。

这里只注册本期真实暴露的接口；旧 mock、health、planning logs 等接口不再挂载。
"""

from fastapi import APIRouter

from .routers import actions, tracking, trip_entry, trip_plans

router = APIRouter()

router.include_router(trip_entry.router)
router.include_router(trip_plans.router)
router.include_router(tracking.router)
router.include_router(actions.router)

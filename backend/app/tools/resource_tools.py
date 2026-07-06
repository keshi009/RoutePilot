"""资源获取工具（mock RPC）。

用 LangChain @tool 封装"获取订单/用户/商家/POI/热点/天气"等资源能力，
统一返回 ToolResult。**这些就是未来替换为公司内部 RPC 的接缝** —— 换实现时
保持工具签名与 ToolResult 契约不变，上层 Agent 无感。

约束：
- mock 边界严格限定在"资源获取"，不 mock 业务逻辑（打分/约束/路线是真实代码）。
- 每个工具 try/except 全包，失败返回 status="error" 的 ToolResult，绝不抛异常。
- 固定工作流由节点代码直接 .invoke 调用，不走 LLM tool-calling。
"""

from __future__ import annotations

import time
from typing import Optional

from langchain_core.tools import tool
from loguru import logger

from app.contracts import ToolResult
from app.mock import fixtures


def _timed(tool_name: str, fn, trace_id: str = "") -> ToolResult:
    """统一执行 + 计时 + 异常兜底，产出 ToolResult。"""

    start = time.monotonic()
    try:
        data, summary = fn()
        latency = int((time.monotonic() - start) * 1000)
        return ToolResult(
            tool_name=tool_name, status="success", summary=summary,
            data=data, latency_ms=latency, trace_id=trace_id,
        )
    except Exception as exc:  # noqa: BLE001 - 工具边界统一兜底
        latency = int((time.monotonic() - start) * 1000)
        logger.warning(f"[trace_id={trace_id}] 资源工具 {tool_name} 失败: {exc}")
        return ToolResult(
            tool_name=tool_name, status="error", summary=f"{tool_name} 调用失败",
            error=str(exc), latency_ms=latency, trace_id=trace_id,
        )


@tool
def fetch_user_profile(user_id: str, trace_id: str = "") -> dict:
    """获取用户画像与当前位置（含偏好标签、周末偏好时间窗）。"""

    def _run():
        user = fixtures.get_user(user_id)
        return {"user": user.model_dump(by_alias=True)}, f"用户 {user.display_name}@{user.city}"

    return _timed("fetch_user_profile", _run, trace_id).model_dump(by_alias=True)


@tool
def fetch_unused_orders(user_id: str, scenario: Optional[str] = None, trace_id: str = "") -> dict:
    """获取用户的待使用订单列表（团购券等）。"""

    def _run():
        orders = fixtures.get_unused_orders(user_id, scenario)
        return {"orders": [o.model_dump(by_alias=True) for o in orders]}, f"待使用订单 {len(orders)} 条"

    return _timed("fetch_unused_orders", _run, trace_id).model_dump(by_alias=True)


@tool
def fetch_merchant_info(merchant_id: str, trace_id: str = "") -> dict:
    """获取商家信息 + 营业时间。"""

    def _run():
        merchant = fixtures.get_merchant(merchant_id)
        hours = fixtures.get_business_hours(merchant_id)
        return {
            "merchant": merchant.model_dump(by_alias=True) if merchant else None,
            "business_hours": hours.model_dump(by_alias=True) if hours else None,
        }, (merchant.name if merchant else f"商家 {merchant_id} 不存在")

    return _timed("fetch_merchant_info", _run, trace_id).model_dump(by_alias=True)


@tool
def fetch_interest_signals(user_id: str, trace_id: str = "") -> dict:
    """获取用户兴趣资产（收藏/浏览/搜索/点赞/购买等信号）。"""

    def _run():
        signals = fixtures.get_interest_signals(user_id)
        return {"interests": [s.model_dump(by_alias=True) for s in signals]}, f"兴趣信号 {len(signals)} 条"

    return _timed("fetch_interest_signals", _run, trace_id).model_dump(by_alias=True)


@tool
def fetch_nearby_pois(lat: float, lng: float, radius_m: int = 5000,
                      scenario: Optional[str] = None, trace_id: str = "") -> dict:
    """获取指定位置周边的 POI（兴趣点/地标）。"""

    def _run():
        pois = fixtures.get_nearby_pois(lat, lng, radius_m, scenario)
        return {"pois": [p.model_dump(by_alias=True) for p in pois]}, f"周边 POI {len(pois)} 个"

    return _timed("fetch_nearby_pois", _run, trace_id).model_dump(by_alias=True)


@tool
def fetch_local_hotspots(city: str, scenario: Optional[str] = None, trace_id: str = "") -> dict:
    """获取城市本地热点（热榜/展览/活动等）。"""

    def _run():
        hotspots = fixtures.get_local_hotspots(city, scenario)
        return {"hotspots": [h.model_dump(by_alias=True) for h in hotspots]}, f"本地热点 {len(hotspots)} 个"

    return _timed("fetch_local_hotspots", _run, trace_id).model_dump(by_alias=True)


@tool
def fetch_weather(city: str, date: str = "nearest_weekend", trace_id: str = "") -> dict:
    """获取指定城市/日期的天气快照。"""

    def _run():
        weather = fixtures.get_weather(city, date)
        return {"weather": weather.model_dump(by_alias=True) if weather else None}, (
            weather.condition if weather else "无天气数据"
        )

    return _timed("fetch_weather", _run, trace_id).model_dump(by_alias=True)


DEFAULT_RESOURCE_TOOLS = (
    fetch_user_profile,
    fetch_unused_orders,
    fetch_merchant_info,
    fetch_interest_signals,
    fetch_nearby_pois,
    fetch_local_hotspots,
    fetch_weather,
)

"""资源工具层（mock RPC，未来替换为公司内部 RPC）。

集中注册 + 按名查找，供 Agent 节点与（未来的）LLM tool-calling 复用。
"""

from typing import Dict

from app.tools.resource_tools import (
    DEFAULT_RESOURCE_TOOLS,
    fetch_user_profile,
    fetch_unused_orders,
    fetch_merchant_info,
    fetch_interest_signals,
    fetch_nearby_pois,
    fetch_local_hotspots,
    fetch_weather,
)

TOOL_REGISTRY: Dict[str, object] = {t.name: t for t in DEFAULT_RESOURCE_TOOLS}


def get_tool(name: str):
    """按名获取工具；不存在返回 None。"""

    return TOOL_REGISTRY.get(name)


__all__ = [
    "DEFAULT_RESOURCE_TOOLS",
    "TOOL_REGISTRY",
    "get_tool",
    "fetch_user_profile",
    "fetch_unused_orders",
    "fetch_merchant_info",
    "fetch_interest_signals",
    "fetch_nearby_pois",
    "fetch_local_hotspots",
    "fetch_weather",
]

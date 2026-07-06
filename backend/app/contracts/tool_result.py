"""统一工具返回结构 ToolResult。

所有资源工具（mock RPC）统一返回它，未来接真实 RPC 也用同一契约。
借鉴 OnCall-Agent 的 ToolResult 设计：status 三态 + 结构化 data + 埋点字段。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ToolResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tool_name: str = Field(default="", alias="toolName")
    status: Literal["success", "error", "degraded"] = "success"
    summary: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: int = Field(default=0, alias="latencyMs")
    trace_id: str = Field(default="", alias="traceId")

    @property
    def ok(self) -> bool:
        return self.status == "success"

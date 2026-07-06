"""通用值对象：位置、时间窗、打分明细、规则校验。

这些是所有领域模型与 Agent 节点共享的最小构件（Pydantic v2）。
每个字段都带默认值，保证向后兼容。
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Location(BaseModel):
    """经纬度坐标。"""

    lat: float = 0.0
    lng: float = 0.0


class TimeWindow(BaseModel):
    """一个 HH:MM 起止的时间窗。"""

    start: str = ""
    end: str = ""


class ScoreBreakdown(BaseModel):
    """打分明细：总分 + 各正向因子 + 各惩罚项 + 可解释性备注。

    factors/penalties 用于评测与文案生成时解释"为什么推荐"。
    """

    total: float = 0.0
    factors: Dict[str, float] = Field(default_factory=dict)
    penalties: Dict[str, float] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class RuleCheck(BaseModel):
    """一条硬约束/规则的校验结果。severity=blocking 表示行程不可用。"""

    model_config = ConfigDict(populate_by_name=True)

    rule_id: str = Field(default="", alias="ruleId")
    passed: bool = True
    severity: Literal["info", "warning", "blocking"] = "info"
    message: str = ""
    affected_entity_id: Optional[str] = Field(default=None, alias="affectedEntityId")

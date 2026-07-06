"""确定性打分引擎（对齐 PRD 三个公式）。

设计原则（用户强调"规则和打分要好好做"）：
- 权重集中在 WEIGHTS 常量表，可解释、可调、可单测。
- 各分量先归一到 [0,1]，再乘权重求和，避免量纲打架。
- 每个函数返回 ScoreBreakdown(total, factors, penalties, notes)，notes 供文案/评测解释。

三个公式：
- score_anchor : 主锚点订单得分（PRD Step4）
- score_node   : 节点推荐分（PRD 节点推荐分公式）—— 作为 OPTW 的 profit 输入
- score_route  : 路线整体分（PRD 路线整体分公式）—— 多候选路线最终排序
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from app.contracts import (
    InterestSignal,
    Location,
    Merchant,
    Order,
    Poi,
    ScoreBreakdown,
    UserProfile,
)
from app.agent.geo import haversine_meters

# ---- 可调权重表（集中管理） ----
WEIGHTS = {
    "anchor": {
        "usability": 0.22,          # 今天可用
        "expiry_urgency": 0.18,     # 有效期紧迫度
        "distance": 0.20,           # 距离便利度
        "preference": 0.20,         # 用户偏好匹配
        "combo_potential": 0.12,    # 与热点/兴趣组合潜力
        "value": 0.08,              # 订单金额价值
        "pen_reservation": 0.15,    # 预约阻塞（惩罚）
        "pen_queue": 0.10,          # 排队风险（惩罚）
    },
    "node": {
        "profit_value": 0.20,       # 订单价值/POI 价值
        "interest_match": 0.24,     # 用户兴趣匹配
        "distance": 0.18,           # 距离便利
        "heat": 0.14,               # 热点强度
        "rating": 0.14,             # 口碑
        "preference": 0.10,         # 偏好标签匹配
        "pen_detour": 0.12,         # 绕路成本（惩罚）
        "pen_risk": 0.10,           # 履约风险（惩罚）
    },
    "route": {
        "anchor_usage": 0.24,       # 主订单使用概率
        "distance_reason": 0.16,    # 总距离合理性
        "order_reason": 0.14,       # 节点顺序合理性
        "time_feasible": 0.16,      # 时间可执行性
        "interest_rich": 0.16,      # 兴趣丰富度
        "combo_purchase": 0.14,     # 顺路加购潜力
        "pen_complexity": 0.12,     # 路线复杂度（惩罚）
    },
}

# 距离便利度归一化的参考尺度（米）：约 8km 以上视为不便利。
DISTANCE_SCALE_M = 8000.0


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _distance_score(a: Location, b: Location) -> float:
    """距离越近分越高，线性衰减到 DISTANCE_SCALE_M。"""

    d = haversine_meters(a, b)
    return _clamp01(1.0 - d / DISTANCE_SCALE_M)


def _expiry_urgency(order: Order, today: Optional[date] = None) -> float:
    """有效期越近越紧迫（分越高）。缺失有效期给中性 0.5。"""

    today = today or date.today()
    try:
        valid_until = date.fromisoformat(order.valid_until)
    except (ValueError, TypeError):
        return 0.5
    days_left = (valid_until - today).days
    if days_left <= 0:
        return 1.0
    if days_left >= 90:
        return 0.1
    # 90 天线性衰减：越近 1，越远 0.1。
    return _clamp01(1.0 - days_left / 90.0)


def _preference_match(tags: List[str], prefs: List[str]) -> float:
    """标签与用户偏好的交集占比。"""

    if not tags or not prefs:
        return 0.0
    tagset = set(tags)
    prefset = set(prefs)
    hit = len(tagset & prefset)
    return _clamp01(hit / max(1, len(prefset))) if hit else 0.0


def _interest_match(tags: List[str], interests: List[InterestSignal]) -> float:
    """节点标签/品类与兴趣信号（加权）匹配度。"""

    if not tags or not interests:
        return 0.0
    tagset = set(tags)
    best = 0.0
    for sig in interests:
        cats = set(sig.related_categories) | {sig.label}
        if tagset & cats:
            best = max(best, sig.weight)
    return _clamp01(best)


def score_anchor(order: Order, merchant: Optional[Merchant], user: UserProfile,
                 usable_today: bool, nearby_interest_count: int = 0,
                 today: Optional[date] = None) -> ScoreBreakdown:
    """主锚点订单得分（PRD Step4）。"""

    w = WEIGHTS["anchor"]
    factors, penalties, notes = {}, {}, []

    f_use = 1.0 if usable_today else 0.0
    f_expiry = _expiry_urgency(order, today)
    f_dist = _distance_score(user.current_location, merchant.location) if merchant else 0.0
    f_pref = _preference_match(order.tags + [order.category], user.preference_tags)
    f_combo = _clamp01(nearby_interest_count / 3.0)
    f_value = _clamp01(order.value / 300.0)

    factors["usability"] = w["usability"] * f_use
    factors["expiry_urgency"] = w["expiry_urgency"] * f_expiry
    factors["distance"] = w["distance"] * f_dist
    factors["preference"] = w["preference"] * f_pref
    factors["combo_potential"] = w["combo_potential"] * f_combo
    factors["value"] = w["value"] * f_value

    if merchant:
        penalties["reservation"] = w["pen_reservation"] * _clamp01(merchant.reservation_risk / 100.0)
        penalties["queue"] = w["pen_queue"] * _clamp01(merchant.queue_risk / 100.0)

    if usable_today:
        notes.append("今天可用")
    if f_expiry >= 0.6:
        notes.append("有效期临近")
    if f_dist >= 0.6:
        notes.append("距离较近")

    total = sum(factors.values()) - sum(penalties.values())
    return ScoreBreakdown(total=round(total, 4), factors=_round(factors), penalties=_round(penalties), notes=notes)


def score_node(node_location: Location, tags: List[str], user: UserProfile,
               interests: List[InterestSignal], heat: int = 0, rating: float = 0.0,
               value: int = 0, anchor_location: Optional[Location] = None,
               risk: float = 0.0) -> ScoreBreakdown:
    """节点推荐分（PRD 节点推荐分公式）—— 作为 OPTW 的 profit 输入。"""

    w = WEIGHTS["node"]
    factors, penalties, notes = {}, {}, []

    f_value = _clamp01(value / 300.0) if value else 0.0
    f_interest = _interest_match(tags, interests)
    f_dist = _distance_score(user.current_location, node_location)
    f_heat = _clamp01(heat / 100.0)
    f_rating = _clamp01((rating - 3.5) / 1.5) if rating else 0.0
    f_pref = _preference_match(tags, user.preference_tags)

    factors["profit_value"] = w["profit_value"] * f_value
    factors["interest_match"] = w["interest_match"] * f_interest
    factors["distance"] = w["distance"] * f_dist
    factors["heat"] = w["heat"] * f_heat
    factors["rating"] = w["rating"] * f_rating
    factors["preference"] = w["preference"] * f_pref

    # 绕路成本：相对锚点的额外距离。
    if anchor_location is not None:
        detour = 1.0 - _distance_score(anchor_location, node_location)
        penalties["detour"] = w["pen_detour"] * _clamp01(detour)
    penalties["risk"] = w["pen_risk"] * _clamp01(risk)

    if f_interest >= 0.6:
        notes.append("匹配你的兴趣")
    if f_heat >= 0.8:
        notes.append("当前热度高")

    total = sum(factors.values()) - sum(penalties.values())
    return ScoreBreakdown(total=round(total, 4), factors=_round(factors), penalties=_round(penalties), notes=notes)


def score_route(node_count: int, total_minutes: int, interest_node_count: int,
                anchor_usable: bool, purchase_node_count: int = 0) -> ScoreBreakdown:
    """路线整体分（PRD 路线整体分公式）—— 多候选路线最终排序。"""

    w = WEIGHTS["route"]
    factors, penalties, notes = {}, {}, []

    f_anchor = 1.0 if anchor_usable else 0.3
    # 总距离/时间合理性：时长越接近但不超预算越好，用 1 - t/300 近似。
    f_dist_reason = _clamp01(1.0 - total_minutes / 300.0)
    f_order = 1.0 if node_count >= 2 else 0.0
    f_time = _clamp01(1.0 - total_minutes / 300.0)
    f_interest = _clamp01(interest_node_count / 3.0)
    f_combo = _clamp01(purchase_node_count / 2.0)

    factors["anchor_usage"] = w["anchor_usage"] * f_anchor
    factors["distance_reason"] = w["distance_reason"] * f_dist_reason
    factors["order_reason"] = w["order_reason"] * f_order
    factors["time_feasible"] = w["time_feasible"] * f_time
    factors["interest_rich"] = w["interest_rich"] * f_interest
    factors["combo_purchase"] = w["combo_purchase"] * f_combo

    # 复杂度惩罚：节点越多越复杂。
    penalties["complexity"] = w["pen_complexity"] * _clamp01((node_count - 2) / 3.0)

    if anchor_usable:
        notes.append("主订单今天可用")
    if interest_node_count >= 2:
        notes.append("兴趣丰富")

    total = sum(factors.values()) - sum(penalties.values())
    return ScoreBreakdown(total=round(total, 4), factors=_round(factors), penalties=_round(penalties), notes=notes)


def _round(d: dict) -> dict:
    return {k: round(v, 4) for k, v in d.items()}

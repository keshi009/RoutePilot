"""确定性硬约束（对齐 PRD Step6 路线约束）。

包括：≤5h、2-5 节点、时段/状态过滤、营业时间→时间窗换算、路线校验。
时间统一用"当天分钟数"（0-1439）表示，便于比较与 OR-Tools。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.contracts import BusinessHours, Merchant, Order, Poi, RuleCheck

# ---- 硬约束常量（PRD Step6） ----
MAX_TOTAL_MINUTES = 300      # 总时长最长 5 小时
MIN_NODES = 2                # 至少 2 个节点
MAX_NODES = 5                # 最多 5 个节点


def parse_hhmm(value: str) -> Optional[int]:
    """"HH:MM" -> 当天分钟数；非法返回 None。"""

    if not value or ":" not in value:
        return None
    try:
        h, m = value.split(":", 1)
        minutes = int(h) * 60 + int(m)
    except (ValueError, TypeError):
        return None
    if minutes < 0:
        return None
    # 允许 24:00 之类的收盘表达，clamp 到 1439。
    return min(minutes, 24 * 60 - 1)


def minutes_to_hhmm(minutes: int) -> str:
    """当天分钟数 -> "HH:MM"。"""

    minutes = max(0, min(minutes, 24 * 60 - 1))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def business_day_window(hours: Optional[BusinessHours], weekday: int) -> Optional[Tuple[int, int]]:
    """取某商家在指定 weekday 的营业窗（分钟）。闭店/无数据返回 None。"""

    if not hours:
        return None
    for day in hours.weekly:
        if day.weekday == weekday:
            if day.is_closed:
                return None
            o = parse_hhmm(day.open_time)
            c = parse_hhmm(day.close_time)
            if o is None or c is None or c <= o:
                return None
            return (o, c)
    return None


def order_time_windows_minutes(order: Order) -> List[Tuple[int, int]]:
    """订单可用时间窗（分钟区间列表）。"""

    windows = []
    for tw in order.usable_time_windows:
        s = parse_hhmm(tw.start)
        e = parse_hhmm(tw.end)
        if s is not None and e is not None and e > s:
            windows.append((s, e))
    return windows


def is_order_usable_today(order: Order, merchant: Optional[Merchant],
                          hours: Optional[BusinessHours], weekday: int) -> Tuple[bool, List[str]]:
    """判断订单今天是否可用：状态 + 可用星期 + 商家营业 + 时间窗有交集。

    返回 (可用, 警告列表)。
    """

    warnings: List[str] = []
    if order.status != "unused":
        return False, [f"订单状态为 {order.status}"]
    if order.usable_weekdays and weekday not in order.usable_weekdays:
        return False, ["今天不在订单可用星期内"]
    if merchant and merchant.status != "normal":
        return False, [f"商家状态异常({merchant.status})"]

    biz = business_day_window(hours, weekday)
    if biz is None:
        return False, ["商家今日闭店或无营业数据"]

    order_wins = order_time_windows_minutes(order)
    if order_wins:
        # 订单可用窗与营业窗需有交集。
        has_overlap = any(min(e, biz[1]) - max(s, biz[0]) > 0 for (s, e) in order_wins)
        if not has_overlap:
            return False, ["订单可用时段与商家营业时段无交集"]

    if merchant and merchant.reservation_risk >= 80:
        warnings.append("预约阻塞风险较高")
    if merchant and merchant.queue_risk >= 70:
        warnings.append("排队风险较高")
    return True, warnings


def node_time_window(open_time: str, close_time: str, weekday_window: Optional[Tuple[int, int]] = None) -> Tuple[int, int]:
    """把 POI/商家营业时段换算成 OPTW 的 [earliest, latest] 分钟窗。

    weekday_window 优先（商家按星期），否则用 open/close 字符串。
    """

    if weekday_window:
        return weekday_window
    o = parse_hhmm(open_time)
    c = parse_hhmm(close_time)
    if o is None or c is None or c <= o:
        return (0, MAX_TOTAL_MINUTES * 0 + 24 * 60 - 1)
    return (o, c)


def filter_recommendable(pois: List[Poi]) -> List[Poi]:
    """剔除异常/闭店 POI（对齐 PRD '不推荐异常 POI'）。"""

    return [p for p in pois if p.status == "normal"]


def validate_route(node_count: int, total_minutes: int) -> List[RuleCheck]:
    """校验路线硬约束，返回 RuleCheck 列表；含 blocking 即失败。"""

    checks: List[RuleCheck] = []
    checks.append(RuleCheck(
        rule_id="node_count",
        passed=MIN_NODES <= node_count <= MAX_NODES,
        severity="blocking" if not (MIN_NODES <= node_count <= MAX_NODES) else "info",
        message=f"节点数 {node_count}（要求 {MIN_NODES}-{MAX_NODES}）",
    ))
    checks.append(RuleCheck(
        rule_id="total_duration",
        passed=total_minutes <= MAX_TOTAL_MINUTES,
        severity="blocking" if total_minutes > MAX_TOTAL_MINUTES else "info",
        message=f"总时长 {total_minutes} 分钟（上限 {MAX_TOTAL_MINUTES}）",
    ))
    return checks


def has_blocking(checks: List[RuleCheck]) -> bool:
    return any(c.severity == "blocking" and not c.passed for c in checks)

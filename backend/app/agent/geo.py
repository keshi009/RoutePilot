"""地理计算：haversine 距离 + 距离→时长换算 + 时长矩阵。

一期用直线（haversine）距离近似真实路网，速度用常量便于调参；真实地图 API 二期接入。
"""

from __future__ import annotations

import math
from typing import List

from app.contracts import Location

# 城市通勤混合速度（步行+短途交通）近似值，单位 km/h。写成常量便于调整。
AVERAGE_SPEED_KMH = 18.0
# 每个节点的停留时长（分钟）：用于时间预算与到达时刻推算。
DEFAULT_DWELL_MINUTES = 45


def haversine_meters(a: Location, b: Location) -> float:
    """两点球面距离，单位米。"""

    r = 6371000.0  # 地球半径（米）
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = math.radians(b.lat - a.lat)
    dlng = math.radians(b.lng - a.lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def meters_to_minutes(meters: float) -> int:
    """按平均速度把距离换算成旅行时长（分钟），至少 1 分钟。"""

    if meters <= 0:
        return 0
    minutes = meters / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return max(1, int(round(minutes)))


def build_time_matrix(locations: List[Location]) -> List[List[int]]:
    """节点间旅行时长矩阵（分钟），供 OR-Tools Time 维度使用。

    index 0 约定为起点（用户当前位置）。
    """

    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            matrix[i][j] = meters_to_minutes(haversine_meters(locations[i], locations[j]))
    return matrix

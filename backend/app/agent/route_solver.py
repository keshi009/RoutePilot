"""OPTW 路线求解引擎（选点 + 排序）。

把 PRD Step5+6 建模为 Orienteering Problem with Time Windows (OPTW)：
在时间预算 + 时间窗 + 节点数上限下，选一个节点子集并排序，使收集到的 profit 最大，
其中锚点订单必达。

- 主引擎：Google OR-Tools routing solver（原生支持时间窗、drop 惩罚）。
- 兜底：贪心插入 + 2-opt（OR-Tools 缺失/超时/无解时自动降级）。

调研依据：OPTW 是行程推荐的标准学术建模；OR-Tools 是主流工程实现，
参考 GitHub Haru8-8/route-optimizer 的时间窗建模方式。

输入约定：candidates[0] 必须是起点（用户当前位置，profit=0，非可 drop）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from loguru import logger

# OR-Tools 作为可选依赖，import 失败自动降级到启发式。
try:  # pragma: no cover - 取决于运行环境
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    _ORTOOLS_AVAILABLE = True
except Exception:  # noqa: BLE001
    _ORTOOLS_AVAILABLE = False


@dataclass
class SolveNode:
    """求解器输入节点。index 0 为起点。"""

    ref_id: str                       # 业务 id（order_id / poi_id / "origin"）
    profit: int                       # 收益（起点=0）
    time_window: Tuple[int, int]      # 当天分钟窗 [earliest, latest]
    service_minutes: int = 45         # 停留时长
    mandatory: bool = False           # 是否必达（锚点订单）


@dataclass
class SolveResult:
    ordered_indices: List[int] = field(default_factory=list)   # 含起点，按访问顺序
    arrival_minutes: List[int] = field(default_factory=list)   # 与 ordered_indices 对齐的到达时刻
    total_travel_minutes: int = 0
    engine: str = "heuristic"          # "ortools" | "heuristic"
    feasible: bool = False


def solve_optw(
    nodes: List[SolveNode],
    time_matrix: List[List[int]],
    budget_minutes: int,
    max_stops: int,
    start_minute: int,
    time_limit_seconds: int = 2,
) -> SolveResult:
    """求解 OPTW。优先 OR-Tools，失败降级启发式。

    max_stops 指除起点外最多访问的节点数。
    """

    if _ORTOOLS_AVAILABLE:
        try:
            result = _solve_ortools(nodes, time_matrix, budget_minutes, max_stops, start_minute, time_limit_seconds)
            if result.feasible:
                return result
            logger.warning("OR-Tools 无可行解，降级启发式")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"OR-Tools 求解异常，降级启发式: {exc}")
    return _solve_greedy(nodes, time_matrix, budget_minutes, max_stops, start_minute)


# ---------------- OR-Tools 主引擎 ----------------

def _solve_ortools(nodes, time_matrix, budget_minutes, max_stops, start_minute, time_limit_seconds) -> SolveResult:
    n = len(nodes)
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)  # n 节点, 1 车, depot=0
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return time_matrix[i][j] + nodes[i].service_minutes

    transit_idx = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    # Time 维度：承载时间窗与总预算。
    horizon = 24 * 60
    routing.AddDimension(transit_idx, horizon, horizon, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")

    for node_idx in range(n):
        index = manager.NodeToIndex(node_idx)
        lo, hi = nodes[node_idx].time_window
        time_dim.CumulVar(index).SetRange(int(lo), int(hi))

    # 起点出发时刻。
    start_index = routing.Start(0)
    time_dim.CumulVar(start_index).SetRange(int(start_minute), int(start_minute))

    # 可选节点：非必达节点允许被 drop，drop 惩罚 = profit（收集到才有价值）。
    for node_idx in range(1, n):
        index = manager.NodeToIndex(node_idx)
        if nodes[node_idx].mandatory:
            continue  # 必达不允许 drop
        routing.AddDisjunction([index], int(nodes[node_idx].profit))

    # 总时长预算（起点到终点累计 <= start + budget）。
    end_index = routing.End(0)
    time_dim.CumulVar(end_index).SetMax(int(start_minute + budget_minutes))

    # 节点数上限：用计数维度约束（除起点外 <= max_stops）。
    def unit_callback(from_index):
        node = manager.IndexToNode(from_index)
        return 0 if node == 0 else 1

    unit_idx = routing.RegisterUnaryTransitCallback(unit_callback)
    routing.AddDimension(unit_idx, 0, max_stops, True, "Count")

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromSeconds(max(1, time_limit_seconds))

    solution = routing.SolveWithParameters(params)
    if not solution:
        return SolveResult(engine="ortools", feasible=False)

    ordered, arrivals = [], []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        ordered.append(node)
        arrivals.append(solution.Value(time_dim.CumulVar(index)))
        index = solution.Value(routing.NextVar(index))

    total_travel = _travel_only(ordered, time_matrix)
    return SolveResult(
        ordered_indices=ordered, arrival_minutes=arrivals,
        total_travel_minutes=total_travel, engine="ortools", feasible=len(ordered) >= 2,
    )


# ---------------- 启发式兜底：贪心插入 + 2-opt ----------------

def _solve_greedy(nodes, time_matrix, budget_minutes, max_stops, start_minute) -> SolveResult:
    n = len(nodes)
    # 起点 + 必达节点为初始路线骨架。
    route = [0]
    for i in range(1, n):
        if nodes[i].mandatory:
            route.append(i)

    # 贪心插入：按 profit/新增时长比，逐个尝试插入未选节点。
    remaining = [i for i in range(1, n) if not nodes[i].mandatory]
    while remaining and (len(route) - 1) < max_stops:
        best = None  # (ratio, node, position)
        for node in remaining:
            for pos in range(1, len(route) + 1):
                trial = route[:pos] + [node] + route[pos:]
                ok, travel, _ = _simulate(trial, nodes, time_matrix, start_minute, budget_minutes)
                if not ok:
                    continue
                added = travel - _travel_only(route, time_matrix)
                ratio = nodes[node].profit / max(1, added)
                if best is None or ratio > best[0]:
                    best = (ratio, node, pos)
        if best is None:
            break
        _, node, pos = best
        route = route[:pos] + [node] + route[pos:]
        remaining.remove(node)

    # 2-opt 局部优化：在保持可行的前提下减少旅行时长。
    route = _two_opt(route, nodes, time_matrix, start_minute, budget_minutes)

    ok, travel, arrivals = _simulate(route, nodes, time_matrix, start_minute, budget_minutes)
    return SolveResult(
        ordered_indices=route, arrival_minutes=arrivals,
        total_travel_minutes=travel, engine="heuristic", feasible=ok and len(route) >= 2,
    )


def _simulate(route, nodes, time_matrix, start_minute, budget_minutes):
    """按顺序模拟：返回 (可行, 总旅行时长, 到达时刻列表)。校验时间窗与预算。"""

    t = start_minute
    arrivals = []
    travel = 0
    for k, node in enumerate(route):
        if k > 0:
            leg = time_matrix[route[k - 1]][node]
            t += leg + nodes[route[k - 1]].service_minutes
            travel += leg
        lo, hi = nodes[node].time_window
        if t < lo:
            t = lo  # 早到等待
        if t > hi:
            return False, travel, arrivals
        arrivals.append(t)
    if (t - start_minute) > budget_minutes:
        return False, travel, arrivals
    return True, travel, arrivals


def _two_opt(route, nodes, time_matrix, start_minute, budget_minutes):
    if len(route) < 4:
        return route
    best = route
    best_travel = _travel_only(route, time_matrix)
    improved = True
    while improved:
        improved = False
        # 固定起点 index 0，不动必达位置的可行性由 _simulate 保证。
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                ok, travel, _ = _simulate(candidate, nodes, time_matrix, start_minute, budget_minutes)
                if ok and travel < best_travel:
                    best, best_travel, improved = candidate, travel, True
    return best


def _travel_only(route, time_matrix) -> int:
    return sum(time_matrix[route[k - 1]][route[k]] for k in range(1, len(route)))


def ortools_available() -> bool:
    return _ORTOOLS_AVAILABLE

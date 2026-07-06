"""路线求解器测试。

验证 OPTW 求解可返回包含必达订单的可行路线，并覆盖 OR-Tools 不可用时的启发式兜底。
"""

from app.agent import route_solver
from app.agent.route_solver import SolveNode, solve_optw


def _sample_problem():
    nodes = [
        SolveNode("origin", 0, (0, 1439), 0, False),
        SolveNode("order_201", 900, (660, 870), 60, True),
        SolveNode("poi_a", 700, (600, 1080), 45, False),
        SolveNode("poi_b", 500, (600, 1080), 45, False),
    ]
    time_matrix = [
        [0, 10, 8, 12],
        [10, 0, 7, 9],
        [8, 7, 0, 6],
        [12, 9, 6, 0],
    ]
    return nodes, time_matrix


def test_solve_optw_returns_feasible_route():
    nodes, time_matrix = _sample_problem()

    result = solve_optw(nodes, time_matrix, budget_minutes=300, max_stops=5, start_minute=630)

    assert result.feasible
    assert result.ordered_indices[0] == 0
    assert 1 in result.ordered_indices
    assert result.engine in {"ortools", "heuristic"}


def test_solve_optw_falls_back_to_heuristic(monkeypatch):
    nodes, time_matrix = _sample_problem()
    monkeypatch.setattr(route_solver, "_ORTOOLS_AVAILABLE", False)

    result = solve_optw(nodes, time_matrix, budget_minutes=300, max_stops=5, start_minute=630)

    assert result.feasible
    assert result.engine == "heuristic"
    assert 1 in result.ordered_indices

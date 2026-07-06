"""LangGraph 固定 7 步工作流。"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    assemble,
    compose_nodes,
    generate_copy,
    identify_assets,
    judge_timing,
    plan_route,
    recall_candidates,
    select_anchor,
)
from app.agent.state import TripPlanState


def _next_or_assemble(next_node: str):
    def _route(state: Dict[str, Any]) -> str:
        return "assemble" if state.get("failure_code") else next_node

    return _route


def build_trip_plan_graph():
    graph = StateGraph(TripPlanState)
    graph.add_node("identify_assets", identify_assets)
    graph.add_node("judge_timing", judge_timing)
    graph.add_node("recall_candidates", recall_candidates)
    graph.add_node("select_anchor", select_anchor)
    graph.add_node("compose_nodes", compose_nodes)
    graph.add_node("plan_route", plan_route)
    graph.add_node("generate_copy", generate_copy)
    graph.add_node("assemble", assemble)

    graph.add_edge(START, "identify_assets")
    graph.add_conditional_edges("identify_assets", _next_or_assemble("judge_timing"))
    graph.add_conditional_edges("judge_timing", _next_or_assemble("recall_candidates"))
    graph.add_conditional_edges("recall_candidates", _next_or_assemble("select_anchor"))
    graph.add_conditional_edges("select_anchor", _next_or_assemble("compose_nodes"))
    graph.add_conditional_edges("compose_nodes", _next_or_assemble("plan_route"))
    graph.add_conditional_edges("plan_route", _next_or_assemble("generate_copy"))
    graph.add_edge("generate_copy", "assemble")
    graph.add_edge("assemble", END)
    return graph.compile()


TRIP_PLAN_GRAPH = build_trip_plan_graph()

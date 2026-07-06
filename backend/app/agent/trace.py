"""结构化 trace 与人读日志（供评测、观察和人工排查）。

每次规划产出一条可回放记录：事件流 + 每步打分快照 + 求解器/LLM 元数据。
落 backend/logs/traces/<trace_id>.jsonl（机器可读）和 <trace_id>.md（人可读）。

纪律（借鉴 OnCall-Agent）：可观测性是旁路，写盘失败只 warning，绝不拖垮主流程。
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

BACKEND_DIR = Path(__file__).resolve().parents[2]
TRACE_DIR = BACKEND_DIR / "logs" / "traces"


STEP_GUIDE = {
    "planner_start": ("规划开始", "初始化请求上下文、trace_id 和默认出发时间。"),
    "identify_assets": ("识别可规划资产", "读取用户、待使用订单和兴趣信号，判断是否有规划基础。"),
    "judge_timing": ("判断可用时机", "逐个订单校验状态、可用星期、营业时间和订单时间窗，并读取天气。"),
    "recall_candidates": ("召回候选节点", "围绕用户当前位置召回周边 POI、热点和兴趣点，并进行节点打分。"),
    "select_anchor": ("选择主锚点订单", "对可用订单打分，选择最值得优先使用的订单作为必达节点。"),
    "compose_nodes": ("组合行程节点", "把锚点订单和高分兴趣点合并成路线求解候选。"),
    "plan_route": ("优化路线排序", "用 OPTW/OR-Tools 求解节点选择和顺序，并执行硬约束校验。"),
    "generate_copy": ("生成展示文案", "基于已验证路线事实生成前端展示文案，失败时降级模板。"),
    "assemble": ("汇总规划结果", "把工作流状态组装成前端可渲染的 TripPlan 或失败结果。"),
    "planner_result": ("规划结束", "记录最终状态、plan_id、失败码和节点数量。"),
    "planner_runtime": ("运行异常", "服务边界兜底，记录不可预期异常。"),
}


def _text(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, list):
        return "、".join(_text(item) for item in value) if value else "-"
    return str(value).replace("\n", " ")


def _cell(value: Any) -> str:
    return _text(value).replace("|", "\\|")


def _table(headers: List[str], rows: List[List[Any]]) -> List[str]:
    if not rows:
        return ["无。"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows)
    return lines


def _score_lines(score: Dict[str, Any], title: str = "打分明细") -> List[str]:
    if not score:
        return [f"### {title}", "无打分明细。"]
    factors = score.get("factors") or {}
    penalties = score.get("penalties") or {}
    notes = score.get("notes") or []
    lines = [f"### {title}", f"- 总分: {_text(score.get('total', 0))}"]
    lines.append("- 正向因子: " + (
        "；".join(f"{name}={_text(value)}" for name, value in factors.items()) if factors else "无"
    ))
    lines.append("- 惩罚项: " + (
        "；".join(f"{name}={_text(value)}" for name, value in penalties.items()) if penalties else "无"
    ))
    lines.append("- 解释: " + (_text(notes) if notes else "无"))
    return lines


def _append_candidate_scores(lines: List[str], candidates: List[Dict[str, Any]], title: str) -> None:
    lines.append(f"### {title}")
    if not candidates:
        lines.append("无。")
        return
    for index, item in enumerate(candidates, start=1):
        name = item.get("name") or item.get("title") or item.get("order_id") or item.get("poi_id")
        ref_id = item.get("order_id") or item.get("poi_id") or "-"
        lines.append(f"#### {index}. {_text(name)} `{_text(ref_id)}`")
        meta = []
        for key, label in (
            ("category", "类别"),
            ("source", "来源"),
            ("merchant_id", "商家"),
            ("distance_m", "距当前位置"),
        ):
            if item.get(key) not in (None, ""):
                suffix = " 米" if key == "distance_m" else ""
                meta.append(f"{label}: {_text(item[key])}{suffix}")
        if meta:
            lines.append("- " + "；".join(meta))
        lines.extend(_score_lines(item.get("score") or {}, "评分拆解"))


def _event_header(event: Dict[str, Any]) -> List[str]:
    step = event.get("step", "")
    title, doing = STEP_GUIDE.get(step, (step, "记录该阶段执行情况。"))
    data = event.get("data") or {}
    sequence = data.get("sequence")
    display = f"{sequence}. {title}" if sequence else title
    return [
        f"## {display} `{step}`",
        f"- 时间: {_text(event.get('ts'))}",
        f"- 状态: {_text(event.get('status'))}",
        f"- 在干嘛: {doing}",
    ]


def _render_event(event: Dict[str, Any]) -> List[str]:
    step = event.get("step", "")
    data = event.get("data") or {}
    lines = _event_header(event)

    if step == "planner_start":
        lines.append(
            f"- 结果: 用户 `{_text(data.get('user_id'))}`，场景 `{_text(data.get('scenario'))}`，目标窗口 `{_text(data.get('target_window'))}`。"
        )

    elif step == "identify_assets":
        orders = data.get("orders") or []
        lines.append(f"- 结果: 识别到 {data.get('order_count', len(orders))} 张待使用订单。")
        lines.append("### 订单资产")
        lines.extend(_table(
            ["订单ID", "标题", "品类", "状态", "价值", "商家ID"],
            [[o.get("order_id"), o.get("title"), o.get("category"), o.get("status"), o.get("value"), o.get("merchant_id")] for o in orders],
        ))

    elif step == "judge_timing":
        usable_ids = data.get("usable_order_ids") or []
        blocked = data.get("blocked_orders") or []
        weather = data.get("weather") or {}
        lines.append(f"- 结果: {_text(data.get('timing_note'))}；可用订单: {_text(usable_ids)}。")
        lines.append(f"- 天气: {_text(weather.get('condition'))}，温度 {_text(weather.get('temperature'))}。")
        lines.append("### 规则过滤结果")
        lines.extend(_table(
            ["订单ID", "拦截原因"],
            [[item.get("order_id"), item.get("warnings")] for item in blocked],
        ))

    elif step == "recall_candidates":
        candidates = data.get("top_candidate_nodes") or []
        lines.append(f"- 结果: 共召回 {data.get('candidate_node_count', len(candidates))} 个候选兴趣节点，下面展示 Top {len(candidates)}。")
        _append_candidate_scores(lines, candidates, "候选 POI 打分 Top 明细")

    elif step == "select_anchor":
        lines.append(f"- 结果: 选择 `{_text(data.get('anchor_order_id'))}` 作为主锚点订单。")
        _append_candidate_scores(lines, data.get("anchor_score_candidates") or [], "锚点订单候选打分明细")
        lines.extend(_score_lines(data.get("anchor_score") or {}, "最终锚点得分"))

    elif step == "compose_nodes":
        nodes = data.get("composed_nodes") or []
        lines.append(f"- 结果: 组合出 {data.get('composed_node_count', len(nodes))} 个路线候选节点。")
        lines.append("### 组合节点")
        lines.extend(_table(
            ["节点ID", "类型", "名称", "时间窗", "打分"],
            [[n.get("id"), n.get("type"), n.get("name"), n.get("time_window"), n.get("score_total")] for n in nodes],
        ))

    elif step == "plan_route":
        route = data.get("route") or {}
        nodes = data.get("ordered_nodes") or []
        lines.append(
            f"- 结果: 使用 `{_text(data.get('route_engine'))}` 求解，输出 {data.get('ordered_node_count', len(nodes))} 个有序节点。"
        )
        lines.append(
            f"- 路线概览: 总距离 {_text(route.get('total_distance_meters'))} 米，总时长 {_text(route.get('total_duration_minutes'))} 分钟，路段数 {_text(route.get('segment_count'))}。"
        )
        lines.append("### 有序路线")
        lines.extend(_table(
            ["顺序", "节点ID", "类型", "名称", "开始", "结束", "节点分"],
            [[idx, n.get("id"), n.get("type"), n.get("name"), n.get("planned_start"), n.get("planned_end"), n.get("score_total")] for idx, n in enumerate(nodes, start=1)],
        ))
        lines.extend(_score_lines(data.get("route_score") or {}, "路线评分拆解"))
        lines.append("### 硬规则约束校验")
        lines.extend(_table(
            ["规则ID", "是否通过", "级别", "说明", "影响对象"],
            [[r.get("rule_id"), r.get("passed"), r.get("severity"), r.get("message"), r.get("affected_entity_id")] for r in data.get("rule_checks") or []],
        ))
        blocking = data.get("blocking_rule_checks") or []
        lines.append(f"- blocking 规则数量: {len(blocking)}。")

    elif step == "generate_copy":
        copy = data.get("copy") or {}
        nodes = data.get("ordered_nodes") or []
        lines.append(
            f"- 结果: 文案 provider=`{_text(copy.get('llm_provider'))}`，标题 `{_text(copy.get('summary_title'))}`，节点文案数 {copy.get('node_copy_count', 0)}。"
        )
        lines.append("### 文案对应节点")
        lines.extend(_table(
            ["节点ID", "类型", "名称", "开始", "结束"],
            [[n.get("id"), n.get("type"), n.get("name"), n.get("planned_start"), n.get("planned_end")] for n in nodes],
        ))

    elif step == "assemble":
        lines.append(
            f"- 结果: plan 状态 `{_text(data.get('plan_status'))}`，plan_id=`{_text(data.get('plan_id'))}`，节点数 {data.get('node_count', 0)}，标题 `{_text(data.get('summary_title'))}`。"
        )

    elif step == "planner_result":
        lines.append(
            f"- 结果: status=`{_text(event.get('status'))}`，plan_id=`{_text(data.get('plan_id'))}`，failure_code=`{_text(data.get('failure_code'))}`，节点数 {data.get('node_count', 0)}。"
        )

    else:
        lines.append(f"- 结果: {json.dumps(data, ensure_ascii=False)}")

    if data.get("failure_code"):
        lines.append(f"- 失败码: `{_text(data.get('failure_code'))}`")
    return lines


class TripTrace:
    """一次行程规划的 trace 收集器。"""

    def __init__(self, trace_id: str, user_id: str = "", scenario: Optional[str] = None):
        self.trace_id = trace_id
        self.user_id = user_id
        self.scenario = scenario
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.events: List[Dict[str, Any]] = []
        self.result: Dict[str, Any] = {}

    def add_event(self, step: str, status: str = "success", latency_ms: int = 0, **data: Any) -> None:
        self.events.append({
            "trace_id": self.trace_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "status": status,
            "latency_ms": latency_ms,
            "data": data,
        })
        logger.bind(trace_id=self.trace_id).info(f"[{step}] status={status} latency={latency_ms}ms {data}")

    @contextmanager
    def step(self, step: str, **static_data: Any):
        """上下文管理器：自动记 latency 与异常。用法 `with trace.step('plan_route') as ev: ev.update(...)`。"""

        start = time.monotonic()
        payload: Dict[str, Any] = dict(static_data)
        try:
            yield payload
            latency = int((time.monotonic() - start) * 1000)
            self.add_event(step, status="success", latency_ms=latency, **payload)
        except Exception as exc:  # noqa: BLE001
            latency = int((time.monotonic() - start) * 1000)
            self.add_event(step, status="error", latency_ms=latency, error=str(exc), **payload)
            raise

    def set_result(self, status: str, failure_code: str = "", plan_id: str = "") -> None:
        self.result = {"status": status, "failure_code": failure_code, "plan_id": plan_id}

    def _render_human_log(self) -> str:
        """把事件流渲染成 Markdown，面向人工排查阅读。"""

        lines = [
            "# RoutePilot 规划过程日志",
            "",
            "## 基本信息",
            f"- trace_id: `{self.trace_id}`",
            f"- user_id: `{_text(self.user_id)}`",
            f"- scenario: `{_text(self.scenario)}`",
            f"- created_at: `{self.created_at}`",
            f"- final_status: `{_text(self.result.get('status'))}`",
            f"- plan_id: `{_text(self.result.get('plan_id'))}`",
            f"- failure_code: `{_text(self.result.get('failure_code'))}`",
            "",
            "## 阅读说明",
            "- 本文件面向人工排查，按规划节点展开“在干嘛”和“结果”。",
            "- JSONL 原始 trace 仍保留在同目录，供机器评测和脚本回放使用。",
            "- 规则约束与打分项会展开显示，便于解释为什么选某个订单、为什么保留或过滤某个节点。",
            "",
        ]
        for event in self.events:
            lines.extend(_render_event(event))
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def flush(self) -> Optional[Dict[str, str]]:
        """落盘为 JSONL + Markdown。失败只 warning，不影响主流程。"""

        try:
            TRACE_DIR.mkdir(parents=True, exist_ok=True)
            jsonl_path = TRACE_DIR / f"{self.trace_id}.jsonl"
            markdown_path = TRACE_DIR / f"{self.trace_id}.md"
            lines = [json.dumps({
                "record": "meta", "trace_id": self.trace_id, "user_id": self.user_id,
                "scenario": self.scenario, "created_at": self.created_at,
            }, ensure_ascii=False)]
            lines += [json.dumps({"record": "event", **e}, ensure_ascii=False) for e in self.events]
            lines.append(json.dumps({"record": "result", "trace_id": self.trace_id, **self.result}, ensure_ascii=False))
            jsonl_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            markdown_path.write_text(self._render_human_log(), encoding="utf-8")
            return {"jsonl": str(jsonl_path), "readable": str(markdown_path)}
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[trace_id={self.trace_id}] trace 落盘失败（不影响主流程）: {exc}")
            return None

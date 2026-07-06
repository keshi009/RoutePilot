"""LLM 文案服务。

确定性路线已经由 Agent 节点生成；这里仅做 Step 7 展示文案。
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from app.agent.prompts import build_copy_prompt
from app.config import get_settings


def _nodes(facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(facts.get("nodes") or [])


def _fallback_copy(facts: Dict[str, Any], provider: str = "fallback", reason: str = "") -> Dict[str, Any]:
    nodes = _nodes(facts)
    anchor = next((n for n in nodes if n.get("type") == "order"), nodes[0] if nodes else {})
    interest = next((n for n in nodes if n.get("type") != "order"), nodes[-1] if nodes else {})

    node_copies = []
    for node in nodes:
        if node.get("type") == "order":
            title = "先用订单"
            node_reason = "今天可用，优先安排"
        else:
            title = "顺路安排"
            notes = node.get("scoreNotes") or []
            node_reason = str(notes[0])[:20] if notes else "兴趣匹配且少绕路"
        node_copies.append({"nodeId": node.get("nodeId", ""), "title": title[:10], "reason": node_reason[:20]})

    return {
        "entryCopy": f"周末可先用{str(anchor.get('name', '订单'))[:8]}，再顺路去{str(interest.get('name', '兴趣点'))[:8]}",
        "summaryTitle": "周末顺路用券",
        "summaryText": "先用周末订单，再顺路安排兴趣点不绕路",
        "nodeCopies": node_copies,
        "llmProvider": provider,
        "fallbackReason": reason,
    }


@lru_cache(maxsize=1)
def _chat_model() -> ChatOpenAI:
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM API key is not configured")
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        max_tokens=settings.llm_max_tokens,
        temperature=0.3,
    )


def _extract_json(content: str) -> Dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def _coerce(payload: Dict[str, Any], facts: Dict[str, Any], provider: str) -> Dict[str, Any]:
    fallback = _fallback_copy(facts, provider=f"{provider}_invalid_fallback", reason="invalid_or_incomplete_json")
    nodes = _nodes(facts)
    known_ids = {n.get("nodeId") for n in nodes}

    node_copies = []
    for item in payload.get("nodeCopies") or []:
        node_id = item.get("nodeId")
        if node_id in known_ids:
            node_copies.append({
                "nodeId": node_id,
                "title": str(item.get("title") or "顺路安排")[:10],
                "reason": str(item.get("reason") or "路线匹配")[:20],
            })

    if len(node_copies) != len(nodes):
        return fallback

    return {
        "entryCopy": str(payload.get("entryCopy") or fallback["entryCopy"])[:36],
        "summaryTitle": str(payload.get("summaryTitle") or fallback["summaryTitle"])[:12],
        "summaryText": str(payload.get("summaryText") or fallback["summaryText"])[:24],
        "nodeCopies": node_copies,
        "llmProvider": provider,
    }


def generate_trip_copy(facts: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()
    trace_logger = logger.bind(trace_id=facts.get("traceId", "-"))
    if settings.routepilot_test_fake_llm:
        trace_logger.info("LLM 文案生成使用测试兜底 provider=test-fake")
        return _fallback_copy(facts, provider="test-fake")

    provider = settings.llm_provider
    try:
        messages = build_copy_prompt(facts)
        trace_logger.info(
            f"LLM 文案生成开始 provider={provider} model={settings.llm_model} node_count={len(_nodes(facts))}"
        )
        result = _chat_model().invoke([
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"]),
        ])
        payload = _coerce(_extract_json(str(result.content)), facts, provider)
        trace_logger.info(f"LLM 文案生成完成 provider={payload.get('llmProvider', provider)}")
        return payload
    except Exception as exc:  # noqa: BLE001 - 文案生成可降级
        trace_logger.warning(f"LLM 文案生成失败，降级模板: {type(exc).__name__}: {str(exc)[:180]}")
        return _fallback_copy(facts, provider=f"{provider}_fallback", reason=f"{type(exc).__name__}: {str(exc)[:160]}")

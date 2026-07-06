"""Step 7 文案生成的 prompt 模板（对齐 PRD 生成约束）。"""

from __future__ import annotations

import json
from typing import Any, Dict, List

SYSTEM_PROMPT = """你是本地生活行程助手的文案生成器。基于给定的"路线事实"生成个性化中文文案。
严格遵守：
1. 行程概述(summaryText)：16-24 字，说清这条路线的价值，不要像广告。
2. 行程主题(summaryTitle)：不超过 12 字。
3. 每个节点标题(title)：不超过 10 字，体现该站在路线中的作用。
4. 每个节点推荐理由(reason)：不超过 20 字，讲清为什么值得去。
5. 只输出 JSON，不要多余文字。
固定叙事结构：路线核心（有什么待使用/感兴趣的）+ 用户关系（今天为什么适合）+ 路线安排（怎么安排的）。
"""


def build_copy_prompt(facts: Dict[str, Any]) -> List[Dict[str, str]]:
    """构造文案生成消息。facts 含 anchor/nodes/weather 等路线事实。"""

    user_content = (
        "路线事实如下（JSON）：\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
        + "\n\n请输出如下 JSON 结构：\n"
        + '{"summaryTitle": "", "summaryText": "", "nodeCopies": [{"nodeId": "", "title": "", "reason": ""}]}'
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

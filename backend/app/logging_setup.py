"""应用日志初始化。

控制台面向开发观察；文件日志使用 JSON 序列化，供后续评测/回放按 trace_id 聚合。
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


BACKEND_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BACKEND_DIR / "logs"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.configure(extra={"trace_id": "-"})
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level}</level> | {extra[trace_id]} | {message}",
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        LOG_DIR / "runtime.jsonl",
        level="INFO",
        serialize=True,
        rotation="20 MB",
        retention="14 days",
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

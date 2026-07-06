"""pytest 全局配置。

测试环境固定启用 fake LLM，避免单测依赖外部模型网络和模型输出稳定性。
"""

import os


def pytest_configure():
    os.environ["ROUTEPILOT_TEST_FAKE_LLM"] = "1"

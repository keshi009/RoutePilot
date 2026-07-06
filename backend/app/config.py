"""集中配置（Pydantic v2 / pydantic-settings）。"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _load_env_files() -> None:
    for path in (ROOT_DIR / ".env", BACKEND_DIR / ".env"):
        if path.exists():
            load_dotenv(dotenv_path=path, override=False)


def _clean(value: Optional[str], default: str = "") -> str:
    return (value or default).strip().strip("`").strip('"').strip("'").strip()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    dashscope_api_key: str = Field(default="", validation_alias="DASHSCOPE_API_KEY")
    dashscope_api_base: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias="DASHSCOPE_API_BASE",
    )
    dashscope_model: str = Field(default="qwen-plus", validation_alias="DASHSCOPE_MODEL")
    dashscope_embedding_model: str = Field(default="text-embedding-v4", validation_alias="DASHSCOPE_EMBEDDING_MODEL")

    routepilot_llm_api_key: str = Field(default="", validation_alias="ROUTEPILOT_LLM_API_KEY")
    routepilot_llm_base_url: str = Field(default="https://api.openai.com/v1", validation_alias="ROUTEPILOT_LLM_BASE_URL")
    routepilot_llm_model: str = Field(default="gpt-4o-mini", validation_alias="ROUTEPILOT_LLM_MODEL")
    routepilot_test_fake_llm: bool = Field(default=False, validation_alias="ROUTEPILOT_TEST_FAKE_LLM")

    llm_timeout_seconds: int = Field(default=25, validation_alias="ROUTEPILOT_LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=1, validation_alias="ROUTEPILOT_LLM_MAX_RETRIES")
    llm_max_tokens: int = Field(default=800, validation_alias="ROUTEPILOT_LLM_MAX_TOKENS")
    stream_max_concurrent: int = Field(default=4, validation_alias="ROUTEPILOT_STREAM_MAX_CONCURRENT")
    stream_queue_size: int = Field(default=64, validation_alias="ROUTEPILOT_STREAM_QUEUE_SIZE")
    stream_timeout_seconds: int = Field(default=180, validation_alias="ROUTEPILOT_STREAM_TIMEOUT_SECONDS")
    stream_heartbeat_seconds: int = Field(default=10, validation_alias="ROUTEPILOT_STREAM_HEARTBEAT_SECONDS")

    @property
    def llm_api_key(self) -> str:
        return _clean(self.dashscope_api_key or self.routepilot_llm_api_key)

    @property
    def llm_base_url(self) -> str:
        base_url = self.dashscope_api_base if self.dashscope_api_key else self.routepilot_llm_base_url
        return _clean(base_url, "https://api.openai.com/v1").rstrip("/")

    @property
    def llm_model(self) -> str:
        model = self.dashscope_model if self.dashscope_api_key else self.routepilot_llm_model
        return _clean(model, "gpt-4o-mini")

    @property
    def llm_provider(self) -> str:
        return "dashscope-compatible" if _clean(self.dashscope_api_key) else "openai-compatible"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_files()
    return Settings()

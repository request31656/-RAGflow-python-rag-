"""统一配置入口。通过 .env 注入，pydantic-settings 校验。

精简后：后端能力全交给 ragflow docker，本项目只做 Streamlit 前端 + ragflow HTTP 薄封装。
保留 langfuse（tracing）和 openai（第二阶段对话生成用），删自建 MySQL/Qdrant/MinIO/embedding。
"""
from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- ragflow（后端核心：解析/检索/存储全交给它）----
    ragflow_base_url: str = "http://localhost:9380"
    ragflow_api_key: str = ""
    # 第二阶段对话用：默认绑定的 dataset_id 和 chat assistant
    ragflow_dataset_id: str = ""

    # ---- LLM（第二阶段对话生成；第一阶段数据侧不用）----
    backend: Literal["simple", "openai"] = "simple"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # ---- Langfuse（tracing，空 key 降级）----
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # ---- Retrieval 默认参数 ----
    top_k: int = 10
    similarity_threshold: float = 0.2
    vector_similarity_weight: float = 0.3


settings = Settings()

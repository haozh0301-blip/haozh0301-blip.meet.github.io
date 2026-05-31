from pathlib import Path
import os
from typing import Any
from urllib.parse import urlparse, urlunparse

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """所有配置仅从 backend/.env 读取，不读取操作系统环境变量。"""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 应用 ──
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8007, validation_alias=AliasChoices("APP_PORT", "PORT"))
    app_reload: bool = True
    storage_dir: str = "Storage"
    max_upload_size_mb: int = 20
    cors_origins: str = "http://localhost:5175"

    # ── 链路开关：ASR → DeepSeek槽位 → 高德MCP → DeepSeek回答 → 百炼TTS ──
    pipeline_asr_enabled: bool = True
    pipeline_slot_enabled: bool = True
    pipeline_amap_enabled: bool = True
    pipeline_answer_enabled: bool = True
    pipeline_tts_enabled: bool = True

    # ── 百炼 ASR ──
    dashscope_api_key: str = ""
    dashscope_asr_url: str = (
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )
    bailian_asr_model: str = "qwen3-asr-flash"
    bailian_asr_language: str = "zh"
    bailian_asr_enable_itn: bool = False
    bailian_asr_stream: bool = False
    bailian_asr_max_base64_mb: int = 10

    # ── DeepSeek 槽位提取 ──
    deepseek_api_key: str = ""
    deepseek_api_url: str = "https://api.deepseek.com/chat/completions"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.1
    deepseek_max_tokens: int = 1024

    # ── DeepSeek 回答生成 ──
    deepseek_answer_model: str = "deepseek-chat"
    deepseek_answer_temperature: float = 0.7
    deepseek_answer_max_tokens: int = 2048

    # ── 百炼 TTS ──
    bailian_tts_url: str = (
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    )
    bailian_tts_model: str = "qwen3-tts-flash"
    bailian_tts_voice: str = "Cherry"
    bailian_tts_language_type: str = "Chinese"

    # ── 高德 MCP（本地 Client → 远端 Server）──
    amap_mcp_enabled: bool = True
    amap_mcp_server_base: str = "https://mcp.amap.com/mcp"
    amap_mcp_url: str = ""
    amap_maps_api_key: str = ""
    amap_web_service_key: str = ""
    amap_mcp_timeout_seconds: int = 120
    amap_mcp_distance_type: int = 0
    amap_http_geocode_fallback: bool = True
    amap_geocode_default_city: str = "北京"
    amap_meet_poi_keywords: str = "商场|咖啡厅|地铁站"
    amap_meet_poi_radius: int = 3000
    amap_meet_candidate_limit: int = 3
    amap_direction_tool: str = "maps_direction_driving"

    @field_validator(
        "bailian_asr_enable_itn",
        "bailian_asr_stream",
        "pipeline_asr_enabled",
        "pipeline_slot_enabled",
        "pipeline_amap_enabled",
        "pipeline_answer_enabled",
        "pipeline_tts_enabled",
        "amap_mcp_enabled",
        "amap_http_geocode_fallback",
        mode="before",
    )
    @classmethod
    def parse_bool(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # 本地开发：仅读 backend/.env，避免系统环境变量干扰
        # 云端部署（Render 等）：设置 MEET_DEPLOY=true，允许 OS 环境变量覆盖 .env
        if os.getenv("MEET_DEPLOY", "").strip().lower() in {"1", "true", "yes", "on"}:
            return (init_settings, env_settings, dotenv_settings, file_secret_settings)
        return (init_settings, dotenv_settings, file_secret_settings)

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path.resolve()

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def bailian_asr_max_base64_bytes(self) -> int:
        return self.bailian_asr_max_base64_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def amap_mcp_url_resolved(self) -> str:
        if self.amap_mcp_url.strip():
            return self.amap_mcp_url.strip()
        key = self.amap_maps_api_key.strip()
        if key:
            base = self.amap_mcp_server_base.rstrip("/")
            return f"{base}?key={key}"
        return ""

    @property
    def amap_web_service_key_resolved(self) -> str:
        return self.amap_web_service_key.strip() or self.amap_maps_api_key.strip()

    @property
    def asr_ready(self) -> bool:
        return self.pipeline_asr_enabled and bool(self.dashscope_api_key.strip())

    @property
    def deepseek_ready(self) -> bool:
        return self.pipeline_slot_enabled and bool(self.deepseek_api_key.strip())

    @property
    def amap_mcp_ready(self) -> bool:
        return (
            self.pipeline_amap_enabled
            and self.amap_mcp_enabled
            and bool(self.amap_mcp_url_resolved)
        )

    @property
    def deepseek_answer_ready(self) -> bool:
        return self.pipeline_answer_enabled and bool(self.deepseek_api_key.strip())

    @property
    def tts_ready(self) -> bool:
        return self.pipeline_tts_enabled and bool(self.dashscope_api_key.strip())

    @property
    def pipeline_ready(self) -> bool:
        return (
            self.asr_ready
            and self.deepseek_ready
            and self.amap_mcp_ready
            and self.deepseek_answer_ready
            and self.tts_ready
        )

    def pipeline_status(self) -> dict[str, Any]:
        return {
            "pipeline": "ASR → DeepSeek槽位 → 高德MCP → DeepSeek回答 → 百炼TTS",
            "ready": self.pipeline_ready,
            "steps": {
                "asr": {
                    "enabled": self.pipeline_asr_enabled,
                    "ready": self.asr_ready,
                    "model": self.bailian_asr_model,
                },
                "deepseek_slot": {
                    "enabled": self.pipeline_slot_enabled,
                    "ready": self.deepseek_ready,
                    "model": self.deepseek_model,
                },
                "amap_mcp": {
                    "enabled": self.pipeline_amap_enabled and self.amap_mcp_enabled,
                    "ready": self.amap_mcp_ready,
                    "server": self.mask_url(self.amap_mcp_url_resolved) or "(未配置 Key)",
                    "geocode_fallback": self.amap_http_geocode_fallback,
                    "candidate_limit": self.amap_meet_candidate_limit,
                },
                "deepseek_answer": {
                    "enabled": self.pipeline_answer_enabled,
                    "ready": self.deepseek_answer_ready,
                    "model": self.deepseek_answer_model,
                },
                "bailian_tts": {
                    "enabled": self.pipeline_tts_enabled,
                    "ready": self.tts_ready,
                    "model": self.bailian_tts_model,
                    "voice": self.bailian_tts_voice,
                },
            },
            "missing": self.pipeline_missing,
        }

    @property
    def pipeline_missing(self) -> list[str]:
        missing: list[str] = []
        if self.pipeline_asr_enabled and not self.dashscope_api_key.strip():
            missing.append("DASHSCOPE_API_KEY")
        if self.pipeline_slot_enabled and not self.deepseek_api_key.strip():
            missing.append("DEEPSEEK_API_KEY")
        if self.pipeline_amap_enabled and self.amap_mcp_enabled:
            if not self.amap_maps_api_key.strip() and not self.amap_mcp_url.strip():
                missing.append("AMAP_MAPS_API_KEY 或 AMAP_MCP_URL")
        return missing

    @staticmethod
    def mask_url(url: str) -> str:
        if not url:
            return ""
        if "key=" not in url:
            return url
        parsed = urlparse(url)
        return urlunparse(parsed._replace(query="key=***"))


settings = Settings()

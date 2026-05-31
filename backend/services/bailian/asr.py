import base64
import json
from pathlib import Path

import httpx
from fastapi import HTTPException

from config import settings
from utils.proxy import clear_proxy_env

CONTENT_TYPE_MAP = {
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".mpeg": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
}


def _resolve_mime_type(file_path: Path, fallback: str | None) -> str:
    mime = CONTENT_TYPE_MAP.get(file_path.suffix.lower())
    if mime:
        return mime
    if fallback:
        return fallback.split(";")[0].strip()
    return "application/octet-stream"


def _build_data_uri(file_path: Path, content_type: str | None) -> str:
    audio_bytes = file_path.read_bytes()
    mime = _resolve_mime_type(file_path, content_type)
    encoded = base64.b64encode(audio_bytes).decode("ascii")
    data_uri = f"data:{mime};base64,{encoded}"

    if len(data_uri.encode("utf-8")) > settings.bailian_asr_max_base64_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"音频 Base64 编码后超过 {settings.bailian_asr_max_base64_mb}MB 限制，"
                "请缩短录音时长"
            ),
        )

    return data_uri


def _extract_transcript(response_data: dict) -> str:
    choices = response_data.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        return "".join(parts).strip()

    return ""


async def transcribe_audio_file(file_path: Path, content_type: str | None) -> dict:
    if not settings.dashscope_api_key:
        raise HTTPException(status_code=500, detail="未配置 DASHSCOPE_API_KEY，请在 backend/.env 中设置")

    clear_proxy_env()

    data_uri = _build_data_uri(file_path, content_type)
    payload = {
        "model": settings.bailian_asr_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": data_uri},
                    }
                ],
            }
        ],
        "stream": settings.bailian_asr_stream,
        "asr_options": {
            "enable_itn": settings.bailian_asr_enable_itn,
        },
    }

    if settings.bailian_asr_language:
        payload["asr_options"]["language"] = settings.bailian_asr_language

    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(trust_env=False, timeout=120.0) as client:
        response = await client.post(
            settings.dashscope_asr_url,
            headers=headers,
            json=payload,
        )

    try:
        response_data = response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"百炼 ASR 返回非 JSON 响应: {response.text[:200]}",
        ) from exc

    if response.status_code >= 400:
        error = response_data.get("error") or {}
        message = error.get("message") or response_data.get("message") or response.text
        raise HTTPException(status_code=502, detail=f"百炼 ASR 调用失败: {message}")

    transcript = _extract_transcript(response_data)

    return {
        "transcript": transcript,
        "raw_response": response_data,
    }

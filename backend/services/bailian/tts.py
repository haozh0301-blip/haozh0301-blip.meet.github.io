import base64
import json
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException

from config import settings
from utils import get_logger, preview_data, save_json_artifact, utc_now_iso
from utils.proxy import clear_proxy_env

logger = get_logger()

CONTENT_TYPE_BY_SUFFIX = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".mpeg": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
}


def _guess_content_type(url: str, header: str | None) -> str:
    if header:
        return header.split(";")[0].strip()
    for suffix, mime in CONTENT_TYPE_BY_SUFFIX.items():
        if url.lower().split("?")[0].endswith(suffix):
            return mime
    return "audio/wav"


async def synthesize_speech(
    text: str,
    *,
    storage_dir: Path,
    stem: str,
) -> dict[str, Any]:
    if not text.strip():
        raise HTTPException(status_code=400, detail="回答文本为空，无法合成语音")

    if not settings.dashscope_api_key:
        raise HTTPException(status_code=500, detail="未配置 DASHSCOPE_API_KEY")

    logger.info("[TTS] 开始 | 文本长度=%s", len(text))
    clear_proxy_env()

    payload = {
        "model": settings.bailian_tts_model,
        "input": {
            "text": text,
            "voice": settings.bailian_tts_voice,
            "language_type": settings.bailian_tts_language_type,
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(trust_env=False, timeout=120.0) as client:
        response = await client.post(
            settings.bailian_tts_url,
            headers=headers,
            json=payload,
        )

        try:
            response_data = response.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"百炼 TTS 返回非 JSON: {response.text[:200]}",
            ) from exc

        if response.status_code >= 400:
            message = (
                response_data.get("message")
                or (response_data.get("error") or {}).get("message")
                or response.text
            )
            raise HTTPException(status_code=502, detail=f"百炼 TTS 调用失败: {message}")

        audio_url, audio_base64_inline = _extract_audio_from_response(response_data)

        audio_bytes: bytes
        content_type: str

        if audio_url:
            logger.info("[TTS] 下载音频 | url=%s", preview_data(audio_url, 120))
            audio_resp = await client.get(audio_url)
            audio_resp.raise_for_status()
            audio_bytes = audio_resp.content
            content_type = _guess_content_type(audio_url, audio_resp.headers.get("content-type"))
        elif audio_base64_inline:
            audio_bytes = base64.b64decode(audio_base64_inline)
            content_type = "audio/wav"
        else:
            raise HTTPException(status_code=502, detail="百炼 TTS 未返回音频 URL 或 Base64 数据")

    suffix = next((ext for ext, mime in CONTENT_TYPE_BY_SUFFIX.items() if mime == content_type), ".wav")
    filename = f"{stem}_tts{suffix}"
    file_path = storage_dir / filename
    file_path.write_bytes(audio_bytes)

    audio_base64 = base64.b64encode(audio_bytes).decode("ascii")
    prefix = storage_dir.name

    artifact = {
        "started_at": utc_now_iso(),
        "request": {
            "model": settings.bailian_tts_model,
            "voice": settings.bailian_tts_voice,
            "text_length": len(text),
        },
        "raw_response": response_data,
        "audio_file": f"{prefix}/{filename}",
        "content_type": content_type,
        "size_bytes": len(audio_bytes),
        "finished_at": utc_now_iso(),
    }
    saved_meta = save_json_artifact(storage_dir, stem, "tts", artifact)

    logger.info(
        "[TTS] 完成 | 文件=%s/%s | 大小=%sKB",
        prefix,
        filename,
        round(len(audio_bytes) / 1024, 1),
    )

    return {
        "audioBase64": audio_base64,
        "audioContentType": content_type,
        "audioUrl": None,
        "artifact": saved_meta,
        "audio_file": {
            "filename": filename,
            "storage_path": f"{prefix}/{filename}",
            "absolute_path": str(file_path),
            "size_bytes": len(audio_bytes),
            "content_type": content_type,
        },
    }


def _extract_audio_from_response(data: dict[str, Any]) -> tuple[str | None, str | None]:
    output = data.get("output") or {}
    audio = output.get("audio") or {}

    url = audio.get("url")
    if url:
        return str(url), None

    inline = audio.get("data")
    if inline:
        return None, str(inline)

    # 兼容其他嵌套形态
    choices = output.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content") or []
        for block in content:
            if isinstance(block, dict) and block.get("audio"):
                audio_obj = block["audio"]
                if isinstance(audio_obj, dict):
                    if audio_obj.get("url"):
                        return str(audio_obj["url"]), None
                    if audio_obj.get("data"):
                        return None, str(audio_obj["data"])

    return None, None

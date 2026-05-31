import json

import httpx
from fastapi import HTTPException

from config import settings
from utils.proxy import clear_proxy_env


async def chat_completion(payload: dict) -> dict:
    if not settings.deepseek_api_key:
        raise HTTPException(status_code=500, detail="未配置 DEEPSEEK_API_KEY，请在 backend/.env 中设置")

    clear_proxy_env()

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(trust_env=False, timeout=120.0) as client:
        response = await client.post(
            settings.deepseek_api_url,
            headers=headers,
            json=payload,
        )

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"DeepSeek 返回非 JSON 响应: {response.text[:200]}",
        ) from exc

    if response.status_code >= 400:
        error = data.get("error") or {}
        message = error.get("message") or data.get("message") or response.text
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用失败: {message}")

    return data

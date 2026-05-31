from typing import Any
from urllib.parse import quote

import httpx

from config import settings
from services.amap.geocode import geocode_with_fallback as _geocode_with_fallback
from services.amap.mcp_post_client import AmapMCPPostClient
from services.amap.parsers import normalize_geo
from utils.proxy import clear_proxy_env

# 向后兼容：推荐模块仍通过 AmapMCPClient 名称引用
AmapMCPClient = AmapMCPPostClient


async def geocode_rest(address: str, city: str) -> dict[str, Any] | None:
    api_key = settings.amap_web_service_key_resolved
    if not api_key:
        return None

    clear_proxy_env()
    query = (
        "https://restapi.amap.com/v3/geocode/geo"
        f"?key={quote(api_key)}"
        f"&address={quote(address)}"
        f"&city={quote(city)}"
    )
    async with httpx.AsyncClient(trust_env=False, timeout=30.0) as client:
        response = await client.get(query)
    data = response.json()
    if str(data.get("status")) != "1":
        return None
    return normalize_geo(data)

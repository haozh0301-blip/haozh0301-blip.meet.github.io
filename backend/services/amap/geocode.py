import re
from typing import Any

from fastapi import HTTPException

from services.amap.parsers import normalize_geo, normalize_pois, parse_location
from utils import get_logger

logger = get_logger()

# 常见简称 → 完整地名
ADDRESS_ALIASES: dict[str, str] = {
    "北京西": "北京西站",
    "北京南": "北京南站",
    "北京东": "北京东站",
    "北京北": "北京北站",
    "上海南": "上海南站",
    "上海虹桥": "虹桥火车站",
}


def strip_city_prefix(address: str, city: str) -> str:
    address = (address or "").strip()
    city = (city or "").strip()
    if not city or not address.startswith(city):
        return address
    remainder = address[len(city) :].strip()
    # 剩余过短（如「西」）时通常是「北京西」等地名本身，不要截断
    if not remainder or len(remainder) < 2:
        return address
    return remainder


def is_low_quality_geo(normalized: dict[str, Any]) -> bool:
    level = str(normalized.get("level") or "").strip()
    if level in {"省", "市", "国家"}:
        return True

    raw = normalized.get("raw")
    if isinstance(raw, dict):
        district = raw.get("district")
        if level in {"兴趣点", "poi"}:
            return False
        if not district and level not in {"村庄", "住宅区", "道路", "道路交叉路口", "公交地铁站点", "地铁站", "火车站"}:
            formatted = str(normalized.get("formatted_address") or "").strip()
            if not formatted:
                return True
    return False


def build_geocode_candidates(address: str, city: str) -> list[str]:
    original = (address or "").strip()
    address = strip_city_prefix(original, city)
    city = (city or "").strip()
    candidates: list[str] = []

    def add(value: str) -> None:
        value = value.strip()
        if value and value not in candidates:
            candidates.append(value)

    alias = ADDRESS_ALIASES.get(address) or ADDRESS_ALIASES.get(original)
    if alias:
        add(alias)

    if re.match(r"^.+[东南西北]$", address) and len(address) <= 6:
        add(f"{address}站")

    add(address)

    # 城市前缀候选放后面，避免「上海东方明珠」落到市级坐标
    if city and address and len(address) <= 4 and city not in address:
        add(f"{city}{address}")
        add(f"{city}{address}站")

    return candidates


def is_mcp_geo_error(raw: Any) -> bool:
    if not isinstance(raw, dict):
        return False
    raw_text = str(raw.get("raw_text") or "")
    return "失败" in raw_text or "ERROR" in raw_text.upper()


async def geocode_via_maps_geo(client, address: str, city: str) -> dict[str, Any] | None:
    raw = await client.call_tool("maps_geo", arguments={"address": address, "city": city})
    if is_mcp_geo_error(raw):
        logger.warning("[高德MCP] maps_geo 引擎错误 | %s/%s | %s", city, address, raw.get("raw_text"))
        return None
    normalized = normalize_geo(raw)
    if normalized and is_low_quality_geo(normalized):
        logger.warning(
            "[高德MCP] maps_geo 结果过粗 | %s/%s | level=%s",
            city,
            address,
            normalized.get("level"),
        )
        return None
    if normalized:
        normalized["via_mcp"] = True
        normalized["query_address"] = address
    return normalized


async def resolve_poi_location(client, poi: dict[str, Any]) -> str:
    location = str(poi.get("location") or "").strip()
    if location:
        return location

    poi_id = poi.get("id")
    if not poi_id or "maps_search_detail" not in client.tool_names:
        return ""

    detail_raw = await client.call_tool("maps_search_detail", arguments={"id": str(poi_id)})
    if isinstance(detail_raw, dict):
        return str(detail_raw.get("location") or "").strip()
    return ""


async def geocode_via_text_search(client, address: str, city: str) -> dict[str, Any] | None:
    if "maps_text_search" not in client.tool_names:
        return None

    raw = await client.call_tool(
        "maps_text_search",
        arguments={"keywords": address, "city": city},
    )
    pois = normalize_pois(raw)
    if not pois:
        return None

    poi = pois[0]
    location = await resolve_poi_location(client, poi)
    if not location:
        return None

    lng, lat = parse_location(location)
    return {
        "lng": lng,
        "lat": lat,
        "formatted_address": poi.get("address") or poi.get("name") or "",
        "level": "poi",
        "raw": poi.get("raw") or poi,
        "via_text_search": True,
        "query_address": address,
    }


async def geocode_with_fallback(
    client,
    *,
    address: str,
    city: str,
    label: str,
    pipeline_log: dict[str, Any],
    geocode_rest_fn,
) -> dict[str, Any]:
    from config import settings

    city = city or settings.amap_geocode_default_city
    candidates = build_geocode_candidates(address, city)

    logger.info("[高德MCP] 地理编码 | %s | 候选=%s", label, candidates)

    for candidate in candidates:
        normalized = await geocode_via_maps_geo(client, candidate, city)
        if normalized:
            logger.info(
                "[高德MCP] 地理编码成功 | %s | 查询=%s | %s",
                label,
                candidate,
                normalized["formatted_address"] or normalized.get("query_address"),
            )
            return normalized

    for candidate in candidates:
        normalized = await geocode_via_text_search(client, candidate, city)
        if normalized:
            pipeline_log["fallback_used"] = True
            pipeline_log["fallback_reason"] = f"{label} maps_geo 失败，已使用 maps_text_search"
            logger.info(
                "[高德MCP] text_search 回退成功 | %s | 查询=%s | %s",
                label,
                candidate,
                normalized["formatted_address"],
            )
            return normalized

    if settings.amap_http_geocode_fallback:
        for candidate in candidates:
            fallback = await geocode_rest_fn(candidate, city)
            if fallback:
                pipeline_log["fallback_used"] = True
                pipeline_log["fallback_reason"] = f"{label} MCP 失败，已 REST 回退"
                fallback["via_mcp"] = False
                fallback["query_address"] = candidate
                logger.info("[高德MCP] REST 回退成功 | %s | %s", label, candidate)
                return fallback

    raise HTTPException(
        status_code=502,
        detail=f"无法地理编码 {label} 的位置: {city} {address}（已尝试: {', '.join(candidates)}）",
    )

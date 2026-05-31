import json
from typing import Any


def extract_tool_json(result: Any) -> Any:
    texts: list[str] = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    if not texts:
        return {}
    combined = "\n".join(texts).strip()
    try:
        return json.loads(combined)
    except json.JSONDecodeError:
        return {"raw_text": combined}


def parse_location(location: str) -> tuple[float, float]:
    lng_str, lat_str = location.split(",", 1)
    return float(lng_str), float(lat_str)


def normalize_geo(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None

    candidates: list[dict] = []
    if isinstance(data.get("results"), list):
        candidates = data["results"]
    elif isinstance(data.get("geocodes"), list):
        candidates = data["geocodes"]

    for item in candidates:
        if not isinstance(item, dict):
            continue
        location = item.get("location")
        if not location:
            continue
        lng, lat = parse_location(str(location))
        return {
            "lng": lng,
            "lat": lat,
            "formatted_address": item.get("formatted_address") or item.get("address") or "",
            "level": item.get("level") or "",
            "raw": item,
        }

    return None


def normalize_pois(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []

    pois = data.get("pois") or data.get("results") or []
    if not isinstance(pois, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in pois:
        if not isinstance(item, dict):
            continue
        location = item.get("location") or ""
        name = item.get("name") or item.get("title") or "未知地点"
        address = item.get("address") or item.get("formatted_address") or ""
        normalized.append(
            {
                "id": item.get("id") or item.get("poi_id") or name,
                "name": name,
                "address": address,
                "location": location,
                "raw": item,
            }
        )
    return normalized


def normalize_direction(data: Any) -> dict[str, str]:
    if not isinstance(data, dict):
        return {"distance": "", "duration": "", "route": ""}

    route = data.get("route") or data
    paths = route.get("paths") or route.get("transits") or []
    if paths and isinstance(paths[0], dict):
        first = paths[0]
        distance_m = first.get("distance") or route.get("distance") or ""
        duration_s = first.get("duration") or route.get("duration") or ""
        return {
            "distance": format_distance(distance_m),
            "duration": format_duration(duration_s),
            "route": first.get("strategy") or "驾车路线",
        }

    return {
        "distance": format_distance(route.get("distance")),
        "duration": format_duration(route.get("duration")),
        "route": "路线规划",
    }


def format_distance(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        meters = float(value)
    except (TypeError, ValueError):
        return str(value)
    if meters >= 1000:
        return f"{meters / 1000:.1f}km"
    return f"{int(meters)}m"


def format_duration(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return str(value)
    minutes = max(1, round(seconds / 60))
    return f"{minutes}分钟"

from pathlib import Path
from typing import Any

from fastapi import HTTPException

from config import settings
from services.amap.geocode import geocode_with_fallback
from services.amap.mcp_client import AmapMCPClient, geocode_rest
from services.amap.parsers import normalize_direction, normalize_pois
from utils import get_logger, save_json_artifact, utc_now_iso

logger = get_logger()


async def recommend_meeting_places(
    slots: dict[str, dict[str, str]],
    *,
    storage_dir: Path,
    stem: str,
) -> dict[str, Any]:
    user = slots.get("user") or {}
    friend = slots.get("friend") or {}

    if not user.get("address") or not friend.get("address"):
        raise HTTPException(status_code=400, detail="槽位信息不完整，缺少用户或朋友地址")

    pipeline_log: dict[str, Any] = {
        "request_id": stem,
        "mcp_url_host": settings.mask_url(settings.amap_mcp_url_resolved),
        "mcp_enabled": settings.amap_mcp_enabled,
        "started_at": utc_now_iso(),
        "input_slots": slots,
        "steps": [],
        "selected_tools": [],
        "normalized_result": {},
        "fallback_used": False,
        "fallback_reason": None,
        "finished_at": None,
    }

    logger.info(
        "[碰面推荐] 开始 | user=%s/%s friend=%s/%s",
        user.get("city"),
        user.get("address"),
        friend.get("city"),
        friend.get("address"),
    )

    recommendations: list[dict[str, Any]] = []

    async with AmapMCPClient(settings.amap_mcp_url_resolved, pipeline_log) as client:
        user_geo = await geocode_with_fallback(
            client,
            address=user["address"],
            city=user.get("city") or settings.amap_geocode_default_city,
            label="user",
            pipeline_log=pipeline_log,
            geocode_rest_fn=geocode_rest,
        )
        friend_geo = await geocode_with_fallback(
            client,
            address=friend["address"],
            city=friend.get("city") or settings.amap_geocode_default_city,
            label="friend",
            pipeline_log=pipeline_log,
            geocode_rest_fn=geocode_rest,
        )

        mid_lng = (user_geo["lng"] + friend_geo["lng"]) / 2
        mid_lat = (user_geo["lat"] + friend_geo["lat"]) / 2
        mid_location = f"{mid_lng:.6f},{mid_lat:.6f}"

        poi_raw = None
        if "maps_around_search" in client.tool_names:
            poi_raw = await client.call_tool(
                "maps_around_search",
                arguments={
                    "location": mid_location,
                    "keywords": settings.amap_meet_poi_keywords,
                    "radius": str(settings.amap_meet_poi_radius),
                },
            )
        elif "maps_text_search" in client.tool_names:
            city = user.get("city") or friend.get("city") or settings.amap_geocode_default_city
            poi_raw = await client.call_tool(
                "maps_text_search",
                arguments={
                    "keywords": settings.amap_meet_poi_keywords.replace("|", " "),
                    "city": city,
                },
            )
        else:
            raise HTTPException(status_code=502, detail="高德 MCP 缺少 POI 搜索工具")

        pois = normalize_pois(poi_raw)[: settings.amap_meet_candidate_limit]
        logger.info("[碰面推荐] POI 候选数=%s", len(pois))

        user_origin = f"{user_geo['lng']},{user_geo['lat']}"
        friend_origin = f"{friend_geo['lng']},{friend_geo['lat']}"
        direction_tool = (
            settings.amap_direction_tool
            if settings.amap_direction_tool in client.tool_names
            else None
        )
        if not direction_tool and "maps_direction_driving" in client.tool_names:
            direction_tool = "maps_direction_driving"

        for index, poi in enumerate(pois):
            poi_location = poi.get("location") or mid_location
            user_route = {"distance": "", "duration": "", "route": ""}
            friend_route = {"distance": "", "duration": "", "route": ""}

            if direction_tool:
                user_dir_raw = await client.call_tool(
                    direction_tool,
                    arguments={"origin": user_origin, "destination": poi_location},
                )
                friend_dir_raw = await client.call_tool(
                    direction_tool,
                    arguments={"origin": friend_origin, "destination": poi_location},
                )
                user_route = normalize_direction(user_dir_raw)
                friend_route = normalize_direction(friend_dir_raw)
            elif "maps_distance" in client.tool_names:
                user_dist_raw = await client.call_tool(
                    "maps_distance",
                    arguments={
                        "origins": user_origin,
                        "destination": poi_location,
                        "type": str(settings.amap_mcp_distance_type),
                    },
                )
                friend_dist_raw = await client.call_tool(
                    "maps_distance",
                    arguments={
                        "origins": friend_origin,
                        "destination": poi_location,
                        "type": str(settings.amap_mcp_distance_type),
                    },
                )
                user_route = {"distance": str(user_dist_raw), "duration": "", "route": "直线距离"}
                friend_route = {"distance": str(friend_dist_raw), "duration": "", "route": "直线距离"}

            recommendations.append(
                {
                    "id": str(poi.get("id") or index + 1),
                    "name": poi.get("name") or f"候选地点{index + 1}",
                    "address": poi.get("address") or "",
                    "distance": {
                        "user": user_route.get("distance") or "",
                        "friend": friend_route.get("distance") or "",
                    },
                    "duration": {
                        "user": user_route.get("duration") or "",
                        "friend": friend_route.get("duration") or "",
                    },
                    "route": user_route.get("route") or "",
                }
            )

    pipeline_log["normalized_result"] = {
        "recommendations": recommendations,
        "candidate_count": len(recommendations),
    }
    pipeline_log["finished_at"] = utc_now_iso()

    artifact = save_json_artifact(storage_dir, stem, "mcp", pipeline_log)
    logger.info("[碰面推荐] 完成 | 候选=%s | MCP留档=%s", len(recommendations), artifact["storage_path"])

    return {
        "recommendations": recommendations,
        "artifact": artifact,
        "pipeline_log": pipeline_log,
    }

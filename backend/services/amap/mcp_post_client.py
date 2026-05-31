"""高德 MCP 专用 POST-only 客户端。

高德远端 Server (mcp.amap.com) 不支持 Streamable HTTP 的 GET/SSE 监听，
官方 Python SDK 在 initialize 后会发 GET，导致背景错误：
  {"error":{"code":-32000,"message":"Method not allowed"}}

本模块仅使用 POST JSON-RPC，与高德服务端实际能力对齐。
"""

import json
from typing import Any

import httpx
from fastapi import HTTPException

from config import settings
from utils import get_logger, preview_data, utc_now_iso
from utils.proxy import clear_proxy_env

logger = get_logger()

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


class AmapMCPPostClient:
    def __init__(self, url: str, pipeline_log: dict[str, Any]):
        self.url = url
        self.pipeline_log = pipeline_log
        self._client: httpx.AsyncClient | None = None
        self._session_id: str | None = None
        self._protocol_version: str | None = None
        self._request_id = 0
        self.tool_names: list[str] = []

    async def __aenter__(self):
        clear_proxy_env()
        self._client = httpx.AsyncClient(trust_env=False, timeout=float(settings.amap_mcp_timeout_seconds))
        logger.info("[高德MCP] POST 连接远端 Server | url=%s", settings.mask_url(self.url))

        await self._run_step("initialize", self._initialize)
        await self._run_step("notifications/initialized", self._send_initialized)
        tools = await self._run_step("list_tools", self._list_tools)
        self.tool_names = [t["name"] for t in tools]
        self.pipeline_log["selected_tools"] = self.tool_names
        logger.info("[高德MCP] 工具列表 | %s", ", ".join(self.tool_names))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self) -> dict[str, str]:
        headers = dict(MCP_HEADERS)
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        if self._protocol_version:
            headers["mcp-protocol-version"] = self._protocol_version
        return headers

    async def _post(self, body: dict[str, Any]) -> tuple[int, dict[str, Any] | None, str]:
        assert self._client is not None
        response = await self._client.post(self.url, json=body, headers=self._headers())
        session_id = response.headers.get("mcp-session-id")
        if session_id:
            self._session_id = session_id

        raw_text = response.text
        if response.status_code == 202 or not raw_text.strip():
            return response.status_code, None, raw_text

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"高德 MCP 返回非 JSON: {raw_text[:200]}",
            ) from exc

        if "error" in data:
            err = data["error"]
            raise HTTPException(
                status_code=502,
                detail=f"高德 MCP 错误 [{err.get('code')}]: {err.get('message')}",
            )

        return response.status_code, data, raw_text

    async def _initialize(self) -> dict[str, Any]:
        _, data, _ = await self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "meet-backend", "version": "1.0.0"},
                },
            }
        )
        result = (data or {}).get("result") or {}
        self._protocol_version = str(result.get("protocolVersion") or "2024-11-05")
        return result

    async def _send_initialized(self) -> dict[str, str]:
        status, _, _ = await self._post(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
        )
        return {"status": status}

    async def _list_tools(self) -> list[dict[str, Any]]:
        _, data, _ = await self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
                "params": {},
            }
        )
        tools = ((data or {}).get("result") or {}).get("tools") or []
        return tools

    async def _run_step(self, name: str, func):
        step = {
            "name": name,
            "started_at": utc_now_iso(),
            "success": False,
            "error": None,
        }
        try:
            result = await func()
            step["success"] = True
            if name == "list_tools":
                step["tools"] = [t["name"] for t in result]
                step["raw_preview"] = preview_data(step["tools"])
            elif name == "initialize":
                step["raw_preview"] = preview_data(result)
            logger.info("[高德MCP] 步骤成功 | %s", name)
            self.pipeline_log["steps"].append(step)
            return result
        except Exception as exc:
            step["error"] = str(exc)
            self.pipeline_log["steps"].append(step)
            logger.error("[高德MCP] 步骤失败 | %s | %s", name, exc)
            raise

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name not in self.tool_names:
            raise HTTPException(
                status_code=502,
                detail=f"高德 MCP 未提供工具 {tool_name}，当前可用: {self.tool_names}",
            )

        step = {
            "name": "call_tool",
            "tool": tool_name,
            "arguments_preview": arguments,
            "started_at": utc_now_iso(),
            "success": False,
            "error": None,
        }
        logger.info("[高德MCP] 调用工具 | %s | 参数=%s", tool_name, preview_data(arguments, 200))

        try:
            _, data, raw_text = await self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                }
            )
            result = (data or {}).get("result") or {}
            payload = _parse_tool_result(result, raw_text)
            step["success"] = True
            step["raw_preview"] = preview_data(payload)
            self.pipeline_log["steps"].append(step)
            logger.info("[高德MCP] 工具返回 | %s | %s", tool_name, preview_data(payload, 160))
            return payload
        except Exception as exc:
            step["error"] = str(exc)
            self.pipeline_log["steps"].append(step)
            logger.error("[高德MCP] 工具失败 | %s | %s", tool_name, exc)
            raise


def _parse_tool_result(result: dict[str, Any], raw_text: str) -> Any:
    content = result.get("content") or []
    texts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("text"):
            texts.append(str(block["text"]))
    if not texts:
        return result or {"raw_text": raw_text}

    combined = "\n".join(texts).strip()
    try:
        return json.loads(combined)
    except json.JSONDecodeError:
        return {"raw_text": combined}

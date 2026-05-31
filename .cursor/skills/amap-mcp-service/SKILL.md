---
name: amap-mcp-service
description: 开发或排查高德地图 MCP 服务时使用。重点约束：如何规范接入高德 MCP、如何记录完整 MCP 调用链、如何避免工具名假设、返回体误判、城市歧义、回退链缺失和密钥泄露等常见错误。
---

# 高德 MCP 服务开发技能

当用户要开发、改造或排查“调用高德 MCP 的后端服务”时，使用这个技能。

这个技能只关注两件事：

1. 按规范开发高德 MCP 服务。
2. 避免真实项目里容易踩的坑。

## 开发规范

默认使用高德远端 Streamable HTTP MCP：

```text
https://mcp.amap.com/mcp?key=<AMAP_KEY>
```

后端服务的最小流程应是：

```text
读取配置
  → 建立 MCP 连接
  → initialize()
  → list_tools()
  → 根据真实工具列表选择工具
  → call_tool(...)
  → 解析并归一化结果
  → 必要时走 REST 回退
  → 记录完整调用链
  → 返回业务响应
```

不要跳过 `list_tools()` 直接假设工具存在。每次接入或升级 SDK 后，都要先跑一次建连 + `list_tools()` 冒烟。

## 环境变量规范

优先支持这些变量：

```env
AMAP_MCP_ENABLED=true
AMAP_MCP_URL=
AMAP_MAPS_API_KEY=
AMAP_WEB_SERVICE_KEY=
AMAP_MCP_DISTANCE_TYPE=0
AMAP_HTTP_GEOCODE_FALLBACK=true
AMAP_GEOCODE_DEFAULT_CITY=
```

规则：

- `AMAP_MCP_URL` 存在时优先使用完整 URL。
- 没有 `AMAP_MCP_URL` 时，用 `AMAP_MAPS_API_KEY` 拼接 MCP URL。
- 如果要支持 REST 回退，必须配置 `AMAP_WEB_SERVICE_KEY`。
- 日志和留档中禁止写入完整 Key，只能记录脱敏值或 URL host。

## Python MCP 写法

依赖建议：

```txt
mcp>=1.14.0
```

Streamable HTTP 推荐写法：

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async with streamable_http_client(url) as streams:
    read_stream, write_stream, *_ = streams
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("maps_geo", arguments={"address": address, "city": city})
```

注意：必须用 `read_stream, write_stream, *_ = streams`，不要写死只接收两个返回值，否则 SDK 升级后可能出现 `ValueError: too many values to unpack`。

## 常用工具

必须以真实 `list_tools()` 返回为准。下面只是常见工具参考：

| 工具名 | 用途 |
| --- | --- |
| `maps_geo` | 地址 → 经纬度 |
| `maps_regeocode` | 经纬度 → 地址 |
| `maps_distance` | 计算距离 |
| `maps_direction_walking` | 步行路线 |
| `maps_direction_driving` | 驾车路线 |
| `maps_direction_transit_integrated` | 公交路线 |
| `maps_text_search` | POI 文本搜索 |
| `maps_around_search` | 周边 POI 搜索 |
| `maps_search_detail` | POI 详情 |

`maps_distance.type` 常见取值：

```text
0 = 直线距离
1 = 驾车距离
3 = 步行距离
```

## 结果解析规范

不要假设 MCP 工具返回体一定等于高德 REST API 返回体。

`maps_geo` 至少要兼容：

```text
MCP 形态：顶层 results[]，元素里包含 location
REST 形态：status + geocodes[]，元素里包含 location
```

解析后建议统一成业务内部结构：

```json
{
  "lng": 120.0,
  "lat": 30.0,
  "formatted_address": "...",
  "level": "...",
  "raw": {}
}
```

解析失败时，必须记录实际返回的顶层 key 和响应摘要，不能只写“解析失败”。

## 留档规范

必须为 MCP 调用链留档，但不要固定要求一定写入 `Storage` 文件夹。由项目根据自身结构选择合适位置，例如：

```text
logs/
storage/
debug/
.sdd/artifacts/
docs/debug/
```

留档内容必须能还原完整 MCP 调用流程，至少包含：

```json
{
  "request_id": "...",
  "mcp_url_host": "https://mcp.amap.com/mcp",
  "mcp_enabled": true,
  "started_at": "...",
  "steps": [
    {
      "name": "initialize",
      "success": true,
      "error": null
    },
    {
      "name": "list_tools",
      "success": true,
      "tools": ["maps_geo", "maps_distance"],
      "raw_preview": {}
    },
    {
      "name": "call_tool",
      "tool": "maps_geo",
      "arguments_preview": {"address": "...", "city": "..."},
      "success": true,
      "raw_preview": {}
    }
  ],
  "selected_tools": [],
  "normalized_result": {},
  "fallback_used": false,
  "fallback_reason": null,
  "finished_at": "..."
}
```

关键要求：

- 从第一次获取工具列表 `list_tools()` 就开始记录。
- 每次 `call_tool()` 都要记录工具名、参数摘要、成功状态、返回摘要。
- 返回摘要要足够排查解析问题，但不能泄露完整 Key、用户隐私或过大的原始数据。
- 如果发生 REST 回退，必须记录 `fallback_used=true` 和 `fallback_reason`。
- 如果调用失败，必须记录错误类型、错误信息和失败阶段。

## 城市与多候选规范

短地点名和重名地点必须谨慎处理：

- 有默认城市时，调用 `maps_geo` 必须传 `city`。
- 多候选时，优先选择匹配默认城市的结果。
- 如果兜底使用首条候选，必须写告警留档，包含候选数量、默认城市和最终选择。
- 距离计算前必须确认两个点都拿到了合法 `lng,lat`。

## REST 回退规范

MCP 失败且配置允许时，可以回退高德 Web 服务：

```http
GET https://restapi.amap.com/v3/geocode/geo?key=<key>&address=<address>&city=<city>
```

回退结果必须显式标记：

```json
{
  "via_mcp": false,
  "fallback_reason": "..."
}
```

不要静默回退。业务响应、日志或调试留档里至少有一处能看出本次结果是否来自 MCP。

## 常见错误

- 跳过 `list_tools()`，直接写死工具名。
- 认为 Cursor 里的 MCP 配置等于后端 `.env` 配置。
- 把 MCP 返回体当成 REST 返回体解析。
- 地名不传城市，导致坐标落到错误城市。
- 调用失败后没有记录原始响应摘要，后续无法排查。
- MCP 失败后想回退 REST，但没有配置 Web 服务 Key。
- 日志里打印完整高德 Key。
- `streamable_http_client` 写死两个返回值，SDK 升级后解包失败。

## 验收清单

完成前至少确认：

1. 后端环境能正常 import `mcp`。
2. MCP URL 解析正确，Key 不会明文出现在日志和留档里。
3. `initialize()` + `list_tools()` 冒烟通过。
4. 留档中能看到从 `list_tools()` 到每次 `call_tool()` 的完整链路。
5. `maps_geo` 能处理真实返回体，并能归一化经纬度。
6. 城市、多候选、缺 Key、MCP 失败、REST 回退路径都被测试过。
7. 业务响应能区分本次结果来自 MCP 还是 REST 回退。

## 详细参考

需要看真实踩坑记录时，读取：

`references/amap-mcp-integration-notes.md`

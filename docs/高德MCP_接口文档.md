# 高德 MCP 接口文档（Meet 项目）

> 整理自 [高德 MCP Server 官方文档](https://lbs.amap.com/api/mcp-server) 及项目接入规范。

---

## 1. 架构

```text
后端 FastAPI
  └── 本地 MCP Client（Python mcp SDK）
        └── Streamable HTTP 连接
              └── 远端高德 MCP Server（mcp.amap.com）
```

**禁止**跳过高德 MCP 直接只用 REST（除非 MCP 失败且开启回退）。

---

## 2. 远端 MCP Server URL

```text
https://mcp.amap.com/mcp?key={AMAP_MAPS_API_KEY}
```

> **注意**：该地址仅支持 **HTTP POST**（JSON-RPC），不支持浏览器直接打开（GET 会返回 `Method not allowed`）。  
> Meet 后端使用 **POST-only MCP Client**，避免官方 SDK 背景 GET 请求触发此错误。

或在 `.env` 中配置完整 URL：

```env
AMAP_MCP_URL=https://mcp.amap.com/mcp?key=xxx
```

---

## 3. Python MCP Client 规范

### 3.1 依赖

```txt
mcp>=1.14.0
```

### 3.2 连接代码

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async with streamable_http_client(url) as streams:
    read_stream, write_stream, *_ = streams  # 必须 *_ 解包
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("maps_geo", arguments={"address": "...", "city": "..."})
```

### 3.3 标准流程

```text
读取 .env 配置
  → 清除代理环境变量
  → streamable_http_client 连接远端 MCP Server
  → initialize()
  → list_tools()          # 禁止跳过
  → call_tool(...)        # 按真实工具名调用
  → 解析归一化结果
  → 完整留档至 Storage
  → （可选）REST 回退
```

---

## 4. 常用工具（以 list_tools 实际返回为准）

| 工具名 | 用途 | 典型参数 |
|--------|------|----------|
| `maps_geo` | 地址 → 经纬度 | `address`, `city` |
| `maps_regeocode` | 经纬度 → 地址 | `location` |
| `maps_distance` | 距离测量 | `origins`, `destination`, `type` |
| `maps_direction_driving` | 驾车路线 | `origin`, `destination` |
| `maps_direction_walking` | 步行路线 | `origin`, `destination` |
| `maps_direction_transit_integrated` | 公交路线 | `origin`, `destination`, `city` |
| `maps_around_search` | 周边 POI | `location`, `keywords`, `radius` |
| `maps_text_search` | 文本 POI 搜索 | `keywords`, `city` |

`maps_distance.type`：`0` 直线 / `1` 驾车 / `3` 步行

---

## 5. 本项目 Meet 推荐流程

1. DeepSeek 提取 `user` / `friend` 的 `city` + `address`
2. MCP `maps_geo` 地理编码两点（必须传 `city`）
3. 计算中点坐标
4. MCP `maps_around_search` 搜索周边碰面 POI（商场/咖啡/地铁等）
5. 对每个候选 POI：
   - `maps_direction_driving` 计算用户 → POI 路线
   - `maps_direction_driving` 计算朋友 → POI 路线
6. 归一化为前端 `recommendations[]` 结构

---

## 6. 返回体解析注意

MCP 工具返回不等于 REST API 原始 JSON，需兼容：

**maps_geo MCP 形态：**

```json
{ "results": [{ "location": "116.39,39.9", "formatted_address": "..." }] }
```

**maps_geo REST 形态：**

```json
{ "status": "1", "geocodes": [{ "location": "116.39,39.9", "formatted_address": "..." }] }
```

归一化后内部结构：

```json
{
  "lng": 116.39,
  "lat": 39.9,
  "formatted_address": "...",
  "raw": {}
}
```

---

## 7. Storage 留档规范（本项目强制）

每次 MCP 调用完整写入：

```text
Storage/{uuid}_mcp.json
```

至少包含：

```json
{
  "request_id": "608c9c93...",
  "mcp_url_host": "https://mcp.amap.com/mcp",
  "started_at": "2026-05-31T15:00:00",
  "steps": [
    { "name": "initialize", "success": true },
    { "name": "list_tools", "success": true, "tools": ["maps_geo", "..."] },
    { "name": "call_tool", "tool": "maps_geo", "arguments": {"address": "...", "city": "北京"}, "success": true, "raw_preview": "..." }
  ],
  "normalized_result": {},
  "fallback_used": false,
  "finished_at": "..."
}
```

**禁止**在留档和日志中写入完整 API Key。

---

## 8. 本项目 `.env` 配置

```env
AMAP_MCP_ENABLED=true
AMAP_MCP_URL=
AMAP_MAPS_API_KEY=
AMAP_WEB_SERVICE_KEY=
AMAP_MCP_DISTANCE_TYPE=0
AMAP_HTTP_GEOCODE_FALLBACK=true
AMAP_GEOCODE_DEFAULT_CITY=北京
AMAP_MEET_POI_KEYWORDS=商场|咖啡厅|地铁站
AMAP_MEET_POI_RADIUS=3000
AMAP_MEET_CANDIDATE_LIMIT=3
```

---

## 9. REST 回退（MCP 失败时）

```http
GET https://restapi.amap.com/v3/geocode/geo?key={AMAP_WEB_SERVICE_KEY}&address={address}&city={city}
```

回退结果必须标记 `via_mcp: false` 和 `fallback_reason`。

---

## 10. 参考链接

- [高德 MCP Server 概述](https://lbs.amap.com/api/mcp-server)
- [快速接入](https://lbs.amap.com/api/mcp-server/gettingstarted)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Web 地理编码](https://lbs.amap.com/api/webservice/guide/api/georegeo)

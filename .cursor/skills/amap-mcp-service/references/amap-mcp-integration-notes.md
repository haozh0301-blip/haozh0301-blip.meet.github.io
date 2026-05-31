# 高德 MCP 集成踩坑与开发规范参考

本参考来自 `docs/高德MCP_集成踩坑与开发规范.md`，用于在开发或排查高德 MCP 服务时按需读取。

## 官方入口

- MCP 服务端概述：<https://lbs.amap.com/api/mcp-server>
- 快速接入：<https://lbs.amap.com/api/mcp-server/gettingstarted>
- npm stdio 包：<https://www.npmjs.com/package/@amap/amap-maps-mcp-server>
- Python MCP SDK：<https://github.com/modelcontextprotocol/python-sdk>
- Web 地理编码：<https://lbs.amap.com/api/webservice/guide/api/georegeo>
- 路径规划 Web 服务：<https://lbs.amap.com/api/webservice/guide/api/direction>
- 控制台：<https://console.amap.com/>

## 接入方式

| 方式 | 说明 | 典型场景 |
| --- | --- | --- |
| Streamable HTTP | 远端 MCP，URL 带 Key 查询参数 | Cursor、后端长连接客户端 |
| Node.js stdio | `npx @amap/amap-maps-mcp-server` | 本地 Agent、子进程 MCP 服务端 |

Streamable HTTP 示例：

```json
{
  "mcpServers": {
    "amap-maps-streamableHTTP": {
      "url": "https://mcp.amap.com/mcp?key=您在高德官网上申请的key"
    }
  }
}
```

Node.js stdio 示例：

```json
{
  "mcpServers": {
    "amap-maps": {
      "command": "npx",
      "args": ["-y", "@amap/amap-maps-mcp-server"],
      "env": {
        "AMAP_MAPS_API_KEY": "您的_Key"
      }
    }
  }
}
```

stdio 场景官方建议 Node v22.14.0 及以上。

## 推荐实现流程

1. 从 `.env` 读取 `AMAP_MCP_URL`，或用 Key 拼 `https://mcp.amap.com/mcp?key=...`。
2. `ClientSession.initialize()` 后调用 `list_tools()`。
3. 用 `maps_geo` 做地址到经纬度。
4. 两点都成功后，调用 `maps_distance` 或路线/POI 工具。
5. 写入 MCP 流水线记录和地理编码摘要，路径由项目结构自行决定。
6. MCP 异常时按配置回退 REST Web 服务。

## 工具名与用途

| 工具名 | 用途 |
| --- | --- |
| `maps_geo` | 地理编码：地址 → 经纬度 |
| `maps_regeocode` | 逆地理编码 |
| `maps_distance` | 距离测量 |
| `maps_direction_walking` | 步行路径规划 |
| `maps_direction_driving` | 驾车路径规划 |
| `maps_direction_transit_integrated` | 公交路径规划 |
| `maps_text_search` | POI 文本搜索 |
| `maps_around_search` | 周边 POI 搜索 |
| `maps_search_detail` | POI 详情 |

`maps_distance.type`:

- `0`: 直线
- `1`: 驾车
- `3`: 步行

## 环境变量

| 变量 | 说明 |
| --- | --- |
| `AMAP_MCP_ENABLED` | 是否优先走 MCP |
| `AMAP_MCP_URL` | 完整 Streamable HTTP URL |
| `AMAP_MAPS_API_KEY` | 拼 MCP URL 的 Key |
| `AMAP_WEB_SERVICE_KEY` | Web 服务 Key，也可作为 MCP URL 拼接 Key |
| `AMAP_MCP_DISTANCE_TYPE` | `maps_distance` 的 `type` |
| `AMAP_HTTP_GEOCODE_FALLBACK` | MCP 异常是否回退 HTTP 地理编码 |
| `AMAP_GEOCODE_ENABLED` | 是否允许 HTTP 地理编码 |
| `AMAP_GEOCODE_DEFAULT_CITY` | 默认城市 |

## 踩坑清单

### 1. Streamable HTTP 解包

做法：

- 使用 `streamable_http_client` 时用 `read_stream, write_stream, *_ = streams`。
- 固定 `mcp` 包下限版本。
- 升级后跑建连 + `list_tools()` 冒烟。

否则：

- SDK 增加第三项时可能出现 `ValueError: too many values to unpack`。

### 2. 工具返回体不一定等于 REST

做法：

- 以 `list_tools` 和真实返回为准。
- `maps_geo` 至少支持两种形态：
  - MCP 形态：顶层 `results[]`，元素有 `location`
  - REST 形态：`status` + `geocodes[]`
- 每种形态保留最小样例。

否则：

- MCP 已通但解析恒失败，容易误判为 Key、配额或服务不可用。

### 3. 默认城市和多候选

做法：

- 短词、重名地传 `city`。
- 优先匹配默认城市候选。
- 兜底首条时打告警。

否则：

- 接口成功但坐标在错误城市，距离和业务文案错误。

### 4. 回退链与密钥分工

做法：

- 文档和 `.env.example` 写清 MCP Key 与 Web 服务 Key。
- MCP 主路径也建议配置 REST Key 以便回退。

否则：

- MCP 抛错后回退因缺 Key 静默跳过。

### 5. 排查顺序

1. 看项目留档中的 MCP 调用链记录：工具列表、步骤、原始响应顶层键。
2. 看项目留档中的地理编码摘要：是否 MCP、错误列表、坐标与地址。
3. 对照 `AMAP_GEOCODE_DEFAULT_CITY` 与落盘 city/address。
4. 变更 `mcp` 或传输层依赖后重新冒烟。

### 6. 文档与实现同步

工具名、默认 URL、`maps_distance.type`、环境变量表、返回形态分支，一旦官方或抓包有变化，必须同步更新技能和实现。

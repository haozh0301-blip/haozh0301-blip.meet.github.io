# DeepSeek 接口文档（Meet 项目）

> 整理自 [DeepSeek API 官方文档](https://api-docs.deepseek.com/zh-cn/)，供本项目 HTTP 调用参考。

---

## 1. 通用规范

| 项 | 说明 |
|----|------|
| 协议 | OpenAI 兼容 REST |
| Base URL | `https://api.deepseek.com` |
| 认证 | `Authorization: Bearer {DEEPSEEK_API_KEY}` |
| 调用方式 | **HTTP**，不使用 SDK |
| 配置来源 | 仅 `backend/.env` |

---

## 2. 对话补全（槽位提取使用）

### 2.1 接口

```http
POST https://api.deepseek.com/chat/completions
Content-Type: application/json
Authorization: Bearer {DEEPSEEK_API_KEY}
```

### 2.2 本项目请求示例（JSON 槽位提取）

```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "从用户描述中提取两人位置，仅输出 JSON。"
    },
    {
      "role": "user",
      "content": "我在北京中关村，朋友在北京望京 SOHO"
    }
  ],
  "response_format": { "type": "json_object" },
  "thinking": { "type": "disabled" },
  "temperature": 0.1,
  "stream": false
}
```

> JSON 模式必须在 system/user 消息中明确要求输出 JSON，否则可能输出空内容。

### 2.3 期望输出结构（业务约定）

```json
{
  "user": { "city": "北京", "address": "中关村" },
  "friend": { "city": "北京", "address": "望京 SOHO" }
}
```

### 2.4 主要请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 如 `deepseek-chat`、`deepseek-v4-flash` |
| `messages` | array | 是 | 对话消息列表 |
| `response_format.type` | string | 否 | `json_object` 启用 JSON 模式 |
| `thinking.type` | string | 否 | `disabled` 关闭思考模式（槽位提取推荐） |
| `temperature` | number | 否 | 0~2，提取任务建议 0~0.3 |
| `max_tokens` | integer | 否 | 最大输出 token |
| `stream` | boolean | 否 | 是否流式，默认 `false` |

### 2.5 响应体（非流式）

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "{\"user\":{\"city\":\"北京\",\"address\":\"中关村\"},\"friend\":{\"city\":\"北京\",\"address\":\"望京 SOHO\"}}"
      }
    }
  ],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

| 字段 | 说明 |
|------|------|
| `choices[0].message.content` | 模型输出（JSON 模式下为 JSON 字符串） |
| `choices[0].finish_reason` | `stop` / `length` / `content_filter` 等 |
| `usage.total_tokens` | Token 消耗 |

### 2.6 错误响应

HTTP 非 2xx 时通常返回：

```json
{
  "error": {
    "message": "错误描述",
    "type": "invalid_request_error",
    "code": "..."
  }
}
```

---

## 3. 本项目 `.env` 配置

```env
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_API_URL=https://api.deepseek.com/chat/completions
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TEMPERATURE=0.1
DEEPSEEK_MAX_TOKENS=1024
```

---

## 4. 本项目调用流程

```text
ASR 文本 → DeepSeek JSON 槽位提取 → 两人 {city, address}
         → 作为参数传入高德 MCP maps_geo / 路线 / 距离工具
```

Storage 留档：

| 文件 | 内容 |
|------|------|
| `{uuid}_slots.json` | DeepSeek 原始响应 + 解析后 slots |

---

## 5. 参考链接

- [对话补全 API](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion)
- [首次调用指南](https://api-docs.deepseek.com/zh-cn/)

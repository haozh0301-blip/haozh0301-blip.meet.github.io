# Meet · 语音碰面推荐

前后端分离的 Web 应用：用麦克风描述你和朋友的所在位置，系统自动推荐合适的碰面地点，并以语音播报结果。

---

## 在线 Demo

| | 链接 |
|---|------|
| **Demo 入口（给他人使用）** | **https://haozh0301-blip.github.io/test/** |
| 后端 API（Render） | https://meet-api.onrender.com |

> 首次部署需按 [docs/DEPLOY.md](docs/DEPLOY.md) 完成 Render 后端 + GitHub Pages 配置。  
> Render 免费版有冷启动，首次请求可能较慢。

---

## 功能概览

- **语音输入**：浏览器麦克风录音，描述两人位置
- **语音识别**：阿里云百炼 Qwen-ASR 将音频转为文字
- **槽位提取**：DeepSeek 从文本中提取两人 `city` + `address`
- **碰面推荐**：高德 MCP 地理编码、中点 POI 搜索、路线/距离计算
- **智能回答**：DeepSeek 生成口语化推荐文案
- **语音播报**：百炼 TTS 合成音频，前端直接播放

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + Vite 6 |
| 后端 | FastAPI + uvicorn |
| ASR / TTS | 阿里云百炼（HTTP） |
| 槽位 / 回答 | DeepSeek（HTTP） |
| 地图 | 高德 MCP（POST-only 本地 Client → 远端 Server） |

---

## 项目结构

```text
.
├── frontend/          # React 前端（端口 5175）
├── backend/           # FastAPI 后端（端口 8007）
│   ├── routers/       # API 路由
│   ├── services/      # ASR、DeepSeek、高德 MCP、TTS
│   ├── Storage/       # 运行时留档（git 忽略，仅保留 .gitkeep）
│   ├── config.py      # 配置（仅读 backend/.env）
│   └── .env.example   # 环境变量模板
├── docs/              # 接口文档
├── 项目思路.md         # 开发思路、踩坑记录、提示词归档
└── README.md
```

---

## 快速开始

### 环境要求

- Node.js 18+
- Python 3.11+

### 1. 克隆仓库

```bash
git clone git@github.com:haozh0301-blip/test.git
cd test
```

### 2. 后端

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY、DEEPSEEK_API_KEY、AMAP_MAPS_API_KEY

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

后端默认运行在 **http://localhost:8007**

健康检查：

```bash
curl http://localhost:8007/api/health
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 **http://localhost:5175**，开发环境通过 Vite 代理将 `/api` 转发到 `8007`。

---

## 配置说明

所有后端配置写在 `backend/.env`，**不要**提交到 Git。主要密钥：

| 变量 | 用途 |
|------|------|
| `DASHSCOPE_API_KEY` | 百炼 ASR + TTS |
| `DEEPSEEK_API_KEY` | 槽位提取 + 回答生成 |
| `AMAP_MAPS_API_KEY` | 高德 MCP（自动拼接 MCP URL） |

完整配置项见 `backend/.env.example`。

---

## 核心接口

### 健康检查

```http
GET /api/health
```

返回各链路步骤（ASR、DeepSeek 槽位、高德 MCP、DeepSeek 回答、TTS）的就绪状态。

### 语音碰面（主接口）

```http
POST /api/meet/voice
Content-Type: multipart/form-data

字段: audio（音频文件，webm/mp4 等）
```

**响应示例（字段摘要）：**

```json
{
  "transcript": "我在北京中关村，朋友在北京望京",
  "slots": {
    "user": { "city": "北京", "address": "中关村" },
    "friend": { "city": "北京", "address": "望京" }
  },
  "recommendations": [
    {
      "name": "鸟巢咖啡",
      "address": "...",
      "distance": { "user": "9.8km", "friend": "7.6km" },
      "duration": { "user": "22分钟", "friend": "23分钟" }
    }
  ],
  "answer": "你们分别在中关村和望京...",
  "audioBase64": "...",
  "audioContentType": "audio/wav"
}
```

---

## 数据留档

每次请求会在 `backend/Storage/` 生成（`{uuid}` 为音频文件名）：

| 文件 | 内容 |
|------|------|
| `{uuid}.webm` | 原始录音 |
| `{uuid}_asr.json` | ASR 识别结果 |
| `{uuid}_slots.json` | DeepSeek 槽位 |
| `{uuid}_mcp.json` | 高德 MCP 完整调用链 |
| `{uuid}_answer.json` | DeepSeek 回答 |
| `{uuid}_tts.json` | TTS 元数据 |

---

## 文档

| 文档 | 说明 |
|------|------|
| [docs/百炼_接口文档.md](docs/百炼_接口文档.md) | ASR / TTS HTTP 调用 |
| [docs/DeepSeek_接口文档.md](docs/DeepSeek_接口文档.md) | 槽位提取与回答生成 |
| [docs/高德MCP_接口文档.md](docs/高德MCP_接口文档.md) | MCP 接入与留档规范 |
| [docs/DEPLOY.md](docs/DEPLOY.md) | 在线 Demo 部署（GitHub Pages + Render） |
| [项目思路.md](项目思路.md) | 完整开发过程、踩坑清单、用户提示词 |

---

## 常见问题

**端口被占用**

```bash
kill $(lsof -t -i :8007)   # 后端
kill $(lsof -t -i :5175)   # 前端
```

**DeepSeek 报 `Insufficient Balance`**  
账户余额不足，需在 [DeepSeek 开放平台](https://platform.deepseek.com/) 充值。

**高德 MCP 报 `Method not allowed`**  
高德远端 MCP 仅支持 POST；本项目已使用 `mcp_post_client.py`，勿在浏览器直接打开 MCP URL。

**地理编码失败（如「北京西」）**  
简称需回退到完整地名（如「北京西站」）；详见 `项目思路.md` 第五节。

**跨城推荐结果不合理**  
当前以两地地理中点搜索 POI，跨城时中点可能落在中间省份；同城场景效果较好。

---

## 许可证

Private / 学习项目

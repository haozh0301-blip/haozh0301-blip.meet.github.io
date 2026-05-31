# 在线 Demo 部署指南

部署后，他人可通过浏览器直接使用 Meet，无需克隆代码。

| 组件 | 平台 | 访问地址 |
|------|------|----------|
| **前端（Demo 入口）** | GitHub Pages | **https://haozh0301-blip.github.io/test/** |
| **后端 API** | Render（免费） | `https://meet-api.onrender.com`（部署后确认） |

---

## 第一步：部署后端到 Render

1. 打开 [Render Dashboard](https://dashboard.render.com/)
2. 点击 **New → Blueprint**
3. 连接 GitHub 仓库 `haozh0301-blip/test`
4. Render 会读取根目录 `render.yaml`，创建名为 `meet-api` 的服务
5. 在 Render 界面填入以下 **Secret** 环境变量（与本地 `.env` 相同）：
   - `DASHSCOPE_API_KEY`
   - `DEEPSEEK_API_KEY`
   - `AMAP_MAPS_API_KEY`
6. 等待部署完成，访问健康检查：
   ```text
   https://meet-api.onrender.com/api/health
   ```
   应返回 `"ready": true`

> **注意**：Render 免费实例 15 分钟无访问会休眠，首次打开 Demo 可能需等待 30~60 秒冷启动。

---

## 第二步：配置 GitHub Pages 前端

### 2.1 启用 GitHub Pages

1. 打开 https://github.com/haozh0301-blip/test/settings/pages
2. **Source** 选择 **GitHub Actions**（不是 Deploy from branch）
3. 保存

### 2.2 设置后端地址变量

1. 打开 https://github.com/haozh0301-blip/test/settings/variables/actions
2. 新建 **Repository variable**：
   - Name: `VITE_API_BASE_URL`
   - Value: `https://meet-api.onrender.com`（你的 Render 后端 URL，**不要**末尾斜杠）

### 2.3 触发部署

推送代码到 `main` 分支会自动部署；或手动：

1. 打开 https://github.com/haozh0301-blip/test/actions
2. 选择 **Deploy Demo (GitHub Pages)** → **Run workflow**

部署成功后，Demo 入口：

```text
https://haozh0301-blip.github.io/test/
```

---

## 第三步：验证 Demo

1. 打开 https://haozh0301-blip.github.io/test/
2. 允许麦克风权限
3. 说：「我在北京中关村，朋友在北京望京」
4. 等待 ASR → 槽位 → 高德 → 回答 → TTS 全链路完成

---

## 常见问题

**页面能打开，但提交录音报错**

- 检查 GitHub Variable `VITE_API_BASE_URL` 是否已设置
- 检查 Render 后端 `/api/health` 是否 `ready: true`
- 检查 Render 环境变量中三个 API Key 是否已填

**CORS 报错**

- Render 中 `CORS_ORIGINS` 需包含 `https://haozh0301-blip.github.io`
- `render.yaml` 已默认配置，若改了 Pages 域名需同步修改

**请求很慢**

- Render 免费版冷启动，第一次请求会慢，属正常现象

**Storage 留档**

- Render 免费版磁盘 ephemeral，重启后留档会丢失；Demo 不受影响

---

## 本地模拟生产构建

```bash
cd frontend
VITE_BASE_PATH=/test/ VITE_API_BASE_URL=https://meet-api.onrender.com npm run build
npm run preview
```

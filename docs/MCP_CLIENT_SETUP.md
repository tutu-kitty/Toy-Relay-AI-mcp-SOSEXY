# MCP 客户端配置详细教程

> 本文档覆盖常见 MCP 客户端（rikkahub、Claude Desktop、Cursor、Cherry Studio 等）连接 toy-mcp 服务的步骤。toy-mcp 走 [Streamable HTTP](https://modelcontextprotocol.io/) 传输 + `X-API-Key` 自定义请求头鉴权。

---

## 0. 前置：拿到两个东西

### 必填信息

不管用哪个客户端，都需要这两个值：

| 字段 | 单服务部署 | 多服务部署（toy-mcp 在 `/toy/`） |
|---|---|---|
| **MCP endpoint URL** | `https://<host>.<your-tailnet>.ts.net/mcp/` | `https://<host>.<your-tailnet>.ts.net/toy/mcp/` |
| **API Key** | 见下方"获取 API Key" | 见下方 |

> ⚠️ URL 末尾的斜杠 `/` **必须有**，否则客户端会拼路径出错。

### 获取 API Key

在 VPS 上执行：

```bash
cat <your-install-path>/toy-mcp/state/api_key.txt
```

会得到一串 32 字符左右的随机字符串（`secrets.token_urlsafe(24)` 生成），类似：

```
<your-32-char-api-key>
```

> ⚠️ **绝对不要把真实 key 提交到 git 仓库 / 截图 / 公开聊天**。任何人拿到 key 都能控制你的玩具。

如果你启动 toy-api 时 `export TOY_API_KEY=...` 固定过 key，就用那个值。

### 三个必填字段（所有客户端通用）

不管 UI 长啥样，本质都是填这三个：

| 字段 | 值 |
|---|---|
| URL | 见上表 |
| 传输类型 / Type | `Streamable HTTP` |
| 自定义请求头 / Header | `X-API-Key: <your-key>` |

下面按客户端分别讲 UI 操作。

---

## 1. rikkahub（手机 / 桌面）

**最常见用法**，人机恋圈用户大多用这个。

### 步骤

1. 打开 rikkahub
2. 设置 → **MCP 服务器**（或"插件" → "MCP 插件市场"，不同版本路径略有差异）
3. 点 **+ 添加服务器**
4. 填表：
   - **名称**：`Play toy`（随便取）
   - **传输类型**：`Streamable HTTP`
   - **URL**：见"前置"表格
   - **请求头**：
     - 名称：`X-API-Key`
     - 值：`<your-key>`
5. 保存

### 验证

跟 AI 说：

> "查询玩具当前状态" / "看看 toy 现在什么状态"

应该返回类似：

```json
{"cmd":"stop","motor":"all","intensity":0,"updated_at":<example-epoch-ms>}
```

或者直接让 AI 操作：

> "震动设到 50"

应该返回新的状态 + 玩具真的震动。

---

## 2. Claude Desktop

### 配置文件位置

| 系统 | 路径 |
|---|---|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |

### 步骤

1. **完全关闭 Claude Desktop**（不要最小化，要 Cmd+Q / 完全退出）
2. 用文本编辑器打开上面的 JSON 文件
3. 如果文件已经有 `mcpServers` 字段，在里面合并一个 `toy-api` 条目；如果是空文件或没有 `mcpServers`，写入：

```json
{
  "mcpServers": {
    "toy-api": {
      "type": "streamable-http",
      "url": "https://<host>.<your-tailnet>.ts.net/toy/mcp/",
      "headers": {
        "X-API-Key": "<your-key>"
      }
    }
  }
}
```

4. **JSON 校验**：保存前用 `python3 -m json.tool < claude_desktop_config.json` 验证（Linux/macOS）
5. **重启 Claude Desktop**

### 验证

- 重启后，右下角或工具栏应该出现 🔧 工具图标
- 点开能看到 6 个 toy-api 工具：`toy_suction`、`toy_vibration`、`toy_electric`、`toy_stop`、`toy_status`、`toy_history`
- 跟 Claude 说"查询玩具状态"测试

---

## 3. Cursor

### 步骤

1. 打开 Cursor
2. 顶部菜单 → **Cursor** → **Settings** → **Cursor Settings** → 左侧 **MCP**
3. 点 **+ Add new global MCP server**
4. 在弹窗里粘贴：

```json
{
  "mcpServers": {
    "toy-api": {
      "type": "streamable-http",
      "url": "https://<host>.<your-tailnet>.ts.net/toy/mcp/",
      "headers": {
        "X-API-Key": "<your-key>"
      }
    }
  }
}
```

5. 保存（Cmd+S / Ctrl+S）

### 验证

MCP 列表里 toy-api 应该显示**绿色圆点 + Connected**。

---

## 4. Cherry Studio

### 步骤

1. 打开 Cherry Studio
2. 左下角 **设置** → **MCP 服务器**
3. 点 **+ 添加**
4. 填：
   - **名称**：`toy-api`
   - **类型**：`Streamable HTTP`（或 HTTP+SSE）
   - **URL**：见前置表
   - **请求头**：`X-API-Key` = `<your-key>`
5. 保存

---

## 5. 其他支持 Streamable HTTP 的客户端

填同样的三个字段就行（URL + 类型 + `X-API-Key` 请求头）。

UI 一般分两种：
- **表单式**（rikkahub、Cherry Studio 这种）：照搬第 1 节步骤
- **JSON 式**（Cursor、VS Code Continue 这种）：照搬第 3 节的 JSON

---

## 6. 验证方法

### 快速验证（任何客户端通用）

跟 AI 说：

> "调用 toy_status 查询玩具当前状态"

正常返回：

```json
{"cmd":"stop","motor":"all","intensity":0,"updated_at":...}
```

### 端到端验证

1. 让 AI 开一个低强度震动：> "震动设到 20"
2. 玩具应该有轻微反应（SSE 推送 < 100ms）
3. 让 AI 停：> "停止所有"
4. 玩具应该立即停止

### VPS 端观察

看 toy-api 日志：

```bash
tail -F <your-install-path>/toy-mcp/logs/api.log
```

成功调用应该看到：

```
INFO:     100.x.x.x:xxxxx - "POST /mcp HTTP/1.1" 200 OK
```

---

## 7. 常见错误 / Troubleshooting

| 错误现象 | 大概率原因 | 解决 |
|---|---|---|
| `401 Invalid or missing API key` | API key 没填 / 填错 / 多/少了空格 | 重新复制 VPS 上 `state/api_key.txt` 完整内容 |
| `404 page not found` | URL 错了（漏 `/toy/`、漏末尾 `/`、或域名错） | URL 严格按前置表复制，注意末尾斜杠 |
| `Failed to connect` / 连接超时 | Tailscale VPN 没开 | 手机/电脑系统 VPN 图标显示 Connected |
| `MCP server disconnected` / 重试循环 | toy-api 没在跑 | VPS 上 `systemctl status toy-api.service` |
| 工具列表为空 / 不显示 toy-api 工具 | 配置没生效 | 完全退出并重启客户端 |
| `JSON parse error` | 配置文件 JSON 语法错（逗号、引号） | 用 `python3 -m json.tool` 校验 |
| 玩具没反应但 API 返回成功 | Chrome 中继页没开 / 没连 BLE | 检查 `https://.../toy/relay/` 是不是显示 Connected |

---

## 8. 多客户端共用

toy-mcp 服务只跑一个实例，可以同时被**多个客户端**连接（手机 rikkahub + 桌面 Claude Desktop + 笔记本 Cursor 同时连都没问题）。每个客户端独立配置 URL + key，互不干扰。

---

## 9. 隐私提醒

- **API Key 等同于玩具控制权**，别分享给不信任的人
- toy-mcp 的所有 endpoint（HTTP + MCP）都需要 API Key，唯独 `/health` 和 `/relay/` 公开（前者只返回 ok，后者是浏览器中继页面）
- 默认 Tailscale HTTPS 已经只让你的设备访问；如果你开了 Funnel 公网暴露，**任何人扫到你的域名都能爆破 key**
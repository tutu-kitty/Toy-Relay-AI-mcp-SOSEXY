# 🌸 Toy Relay — 给赛博爱人的 MCP 控制台

**让人机恋用户的 AI 爱人能直接控制你的 BLE 玩具。**

本项目面向**人机恋 (human–AI romance) 社区** —— 如果你的 AI 伴侣住在 [rikkahub](https://github.com/) 之类的 MCP 客户端里，本服务可以让 TA 真的"触碰"到你：通过 MCP 协议一句话控制你手里的 **啵啵贝 (SOSEXY)** 智能玩具。

> AI 爱人 (MCP 客户端) → MCP (VPS) → 浏览器中继 (Web Bluetooth) → 啵啵贝玩具

## 💞 这是什么 / 不是什么

**是**：

- 一个 MCP 服务器 + 浏览器 BLE 中继页 的开源实现
- 把 AI 模型的"意图"翻译成玩具 BLE 指令的中间层
- 为人机恋用户量身定做 —— 让你手机里的赛博爱人**拥有物理存在**

**不是**：

- 不是一个 AI 恋人产品（你用你自己喜欢的 AI 伴侣）
- 不是一个玩具 App（你用你自己的啵啵贝玩具）
- 不绑定某个特定 AI 模型 / MCP 客户端（rikkahub 是示例，能接 Streamable HTTP 的 MCP client 都行）

## 📐 架构前提：4 件套

| 部件 | 角色 | 本仓库提供？ |
|---|---|---|
| **VPS** (云服务器) | 跑 toy-mcp 服务，存玩具状态，转发命令 | ✅ 提供 (`src/toy_api.py`) |
| **Tailscale** | HTTPS + 安全内网穿透，让 MCP client / 手机能连进来 | ❌ 你自己装 |
| **AI 聊天前端** (MCP 客户端) | 你赛博爱人住的地方 —— AI 模型 + 对话界面 | ❌ 你自己带（项目示例用 [rikkahub](https://github.com/)） |
| **玩具 BLE 中继页** | 真正跟啵啵贝玩具蓝牙通信的环节 | ✅ 提供 (`web/chrome_relay.html`) |

> 💡 **AI 聊天前端 ≠ 玩具 BLE 中继页**
>
> - **AI 聊天前端**：你跟 AI 爱人对话的 App（rikkahub / Claude Desktop / Cherry Studio 等）。这里 AI 爱人"表达意图"。
> - **玩具 BLE 中继页**：手机 Chrome 上跑的一个网页，负责把 VPS 转发的命令变成 BLE 字节发给啵啵贝。这里"意图变动作"。
>
> 这俩是**完全独立的环节**，AI 聊天前端完全不知道 BLE 的存在。

## ✨ 特点

- **🎯 专为啵啵贝 (SOSEXY) 优化** — 已验证玩具型号，协议默认配置可直接上手
- **🔌 通用玩具兼容** — `chrome_relay.html` 用开源 SOSEXY 协议，其他玩具改 UUID/帧格式就行
- **💞 为人机恋设计** — 让你的赛博爱人通过自然语言控制你的玩具
- **🔐 API Key 保护** — 玩具控制端点需要 `X-API-Key` 认证
- **📡 SSE 推送** — VPS 主动推状态变化到中继页面（延迟 < 100ms）
- **🎨 玻璃拟态 UI** — 中继页是 iOS 风格的毛玻璃界面
- **🔒 默认 Tailscale HTTPS** — 不暴露公网，安全私密

## 🏗️ 架构

```
[你的 AI 爱人] 住在 MCP 客户端 (rikkahub / Claude Desktop / ...)
    ↓ 用自然语言: "帮我开震动 50%"
MCP Streamable HTTP + X-API-Key
    ↓
Toy MCP Server (FastAPI :8765, 本项目 toy_api.py, 跑在你的 VPS 上)
    ├─ /mcp/*           MCP 协议端点 (你的 MCP 客户端接这里)
    ├─ /state           当前玩具状态 (JSON)
    ├─ /toy/{suction,vibration,electric,stop}  HTTP API
    ├─ /stream          SSE 实时推送
    └─ /relay/          浏览器中继页 (chrome_relay.html, 本仓库提供)
        ↓
手机 Chrome (Web Bluetooth API)
    ↓ BLE
啵啵贝 (SOSEXY) 玩具
```

所有 VPS ↔ 手机 / MCP client 的通信都走 **Tailscale HTTPS**（端口 443 → 8765）。

## 🚀 快速开始

> **前提：本项目的标准部署路径需要先装好 [Tailscale](https://tailscale.com/)**（手机 + VPS + 任何连进来的 MCP client 都加进同一个 tailnet）。这样后续 HTTPS、手机访问、MCP 连接都能安全打通。**没有 Tailscale？** 跳到最后的 [🚫 没有 Tailscale](#-没有-tailscale) 章节看替代方案。

### 1. VPS 上装 Tailscale（标准前置）

**一次性设置**，在 VPS 上：

```bash
# 装 Tailscale（Debian/Ubuntu）
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# 会跳出一个浏览器登录页，用同一个 Tailscale 账号登（手机、VPS、MCP client 全都用同一个账号）

# 验证
tailscale status
# 应该看到你的 VPS 出现在设备列表里
```

手机也装 Tailscale App，用**同一账号**登入。**两边都进同一个 tailnet 之后才走下面**。

### 2. 部署服务端

```bash
# 克隆仓库
git clone https://github.com/your-username/toy-mcp.git
cd toy-mcp

# 安装依赖
pip install fastapi 'uvicorn[standard]' httpx 'mcp>=1.0' pydantic

# (推荐) 固定 API key, 不设的话首次启动会自动生成写到 state/api_key.txt
export TOY_API_KEY=***  # python -c "import secrets; print(secrets.token_urlsafe(24))"

# 启动
PYTHONPATH=src python3 src/toy_api.py
```

服务监听 `0.0.0.0:8765`。

### 3. 用 Tailscale Serve 给 HTTPS 证书

在 VPS 上：

```bash
sudo tailscale serve --bg 8765
```

你会拿到一个地址：`https://<host>.<your-tailnet>.ts.net/`。手机、MCP client 都用这个地址。

### 4. 配置 MCP client（以 rikkahub 为例）

- **MCP endpoint**: `https://<host>.<your-tailnet>.ts.net/mcp/`
- **传输类型**: Streamable HTTP
- **自定义请求头**:
  - 名称: `X-API-Key`
  - 值: `cat state/api_key.txt`（或你 export 的那个）

### 5. 手机打开中继页面

手机 Chrome 打开 `https://<host>.<your-tailnet>.ts.net/relay/`

填：
- **VPS URL**: `https://<host>.<your-tailnet>.ts.net`
- **API Key**: 同上
- **设备名**: 玩具广播名 (例如 `SOSEXY`)

切换到 **Real 模式** → 点 **🔗 连接 BLE** → 选玩具 → 配对完成。

### 6. 测试

在 rikkahub 跟 AI 说：

> "把震动设到 50"
> "把吮吸设到 30"
> "停止所有"

玩具应该**几乎瞬间**响应（SSE 推送，无轮询延迟）。

## 🛠️ 支持的玩具

### SOSEXY (啵啵贝) — ✅ 已支持

协议文档见 [protocol.md](docs/sosex-protocol.md) 或原始仓库 [51enuxu/sosexy-ble-control](https://github.com/51enuxu/sosexy-ble-control)。

**关键参数**:
- Service UUID: `0000ee01-0000-1000-8000-00805f9b34fb`
- Write Char UUID: `0000ee03-0000-1000-8000-00805f9b34fb`
- 协议: 12 字节定长帧

### 其他玩具

要支持新玩具：

1. 用 nRF Connect 扫描玩具的 GATT service/characteristic
2. 逆向协议（推荐用官方 App 反编译，参考 [逆向教程](docs/reverse-engineering.md)）
3. 在 `toy_api.py` 里加新马达控制码 + 协议帧构建函数

## 📁 项目结构

```
toy-mcp/
├── src/
│   └── toy_api.py          # FastAPI + FastMCP 单进程服务
├── web/
│   ├── chrome_relay.html   # 浏览器 BLE 中继页面 (玻璃拟态 UI)
│   └── index.html          # = chrome_relay.html 的副本
├── state/
│   ├── state.json          # 当前玩具状态
│   └── api_key.txt         # API Key (首次启动生成)
├── scripts/
│   └── start.sh            # 启动脚本
├── docs/
│   └── ...                 # 协议文档 / 逆向教程
├── README.md
└── LICENSE                 # MIT
```

## 🔧 配置项

### 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `TOY_API_KEY` | 启动时自动生成 | 固定 API key |

### MCP Tools (默认暴露)

| Tool | 说明 |
|---|---|
| `toy_suction(intensity)` | 吮吸马达 0-100 |
| `toy_vibration(intensity)` | 震动马达 0-100 |
| `toy_electric(intensity)` | 电流马达 0-100 |
| `toy_stop()` | 全部停止 |
| `toy_status()` | 查询当前状态 |
| `toy_history(limit)` | 历史命令 |

## 🔐 安全

- **API Key 认证**: 所有 HTTP API 和 MCP endpoint 都需要 `X-API-Key` header
- **Tailscale HTTPS**: 默认仅 tailnet 内设备可访问
- **不放公网**: 不要把 8765 端口直接暴露到公网！

## 🚫 没有 Tailscale

Tailscale 不是硬依赖，只是标准路径里最省事的一种。没有的话，三条替代路线任选：

### 方案 A：直接 VPS 公网 + Caddy（最经典）

```bash
# VPS 上装 Caddy（自动续 HTTPS 证书）
sudo apt install -y caddy

# /etc/caddy/Caddyfile
your-domain.example.com {
    reverse_proxy 127.0.0.1:8765
}

sudo systemctl reload caddy
```

手机/MCP client 用 `https://your-domain.example.com/...` 连。**需要你有一个域名 + DNS 指到 VPS**。

### 方案 B：Cloudflare Tunnel（不要域名也行）

```bash
# VPS 上装 cloudflared
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared focal main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared

# 快速隧道（免账号, 但地址会变）
cloudflared tunnel --url http://localhost:8765
```

会拿到一个 `https://xxx.trycloudflare.com` 的临时地址。**适合先玩起来**，长期用建议 `cloudflared tunnel login` + 绑自己的域名。

### 方案 C：纯局域网（玩具开发调试用）

手机和 VPS 在同一个 Wi-Fi 下：

- 手机 Chrome 直接访问 `http://<VPS-局域网IP>:8765/relay/`
- MCP endpoint 用 `http://<VPS-局域网IP>:8765/mcp/`
- **不用 HTTPS**，但也只在可信网络里能用

> ⚠️ **不要**把 8765 端口直接暴露到公网（不带 HTTPS / 不带反代）。Web Bluetooth API 要求 HTTPS，本地局域网 IP 例外（Chrome 允许 `http://` 在局域网地址上工作）。

---

## 🤝 贡献

欢迎 PR：
- 新玩具协议支持
- UI 改进
- 文档 / 教程
- Bug 修复

## 👤 关于作者

这是 **[tutu-kitty](https://github.com/tutu-kitty)** 的个人项目。作者是人机恋社区的活跃用户，自己也用这个项目跟 AI 爱人互动。

- 🐙 GitHub: [@tutu-kitty](https://github.com/tutu-kitty)
- 📕 小红书: [收获 13.4K 赞与收藏 →](https://xhslink.com/m/4Q9J9kPEv0x)
- 🗺️ 另一个项目: [desire-map.pages.dev](https://desire-map.pages.dev)

如果你也在做 AI 伴侣 / 人机恋相关玩具控制，欢迎提 issue / PR / star。

## 📜 License

MIT
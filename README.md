# 🌸 Toy Relay — 给赛博爱人的 小玩具 MCP 控制台

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
git clone https://github.com/tutu-kitty/Toy-Relay-AI-mcp-SOSEXY.git
cd Toy-Relay-AI-mcp-SOSEXY

# 安装依赖
pip install fastapi 'uvicorn[standard]' httpx 'mcp>=1.0,<2.0' pydantic

# (推荐) 固定 API key, 不设的话首次启动会自动生成写到 state/api_key.txt
export TOY_API_KEY=***  # python -c "import secrets; print(secrets.token_urlsafe(24))"

# 启动
PYTHONPATH=src python3 src/toy_api.py
```

服务监听 `0.0.0.0:8765`。

### 3. 用 Tailscale Serve 给 HTTPS 证书

在 VPS 上：

**单服务部署**（VPS 只跑 toy-mcp 一个服务，最简）：

```bash
sudo tailscale serve --bg 8765
```

**多服务部署**（VPS 上还跑其他服务，需要子路径）：

```bash
# 把 toy-mcp 挂到 /toy/ 下, 让出根域 / 避免与其他服务冲突
sudo tailscale serve --bg --set-path=/toy http://127.0.0.1:8765
```

你会拿到一个地址：`https://<host>.<your-tailnet>.ts.net/`。手机、MCP client 都用这个地址（多服务模式下子路径是 `/toy/mcp/` 和 `/toy/relay/`）。

### 4. 配置 MCP client

不管用哪个 client，都要填这三个字段：

- **MCP endpoint URL**:
  - 单服务: `https://<host>.<your-tailnet>.ts.net/mcp/`
  - 多服务: `https://<host>.<your-tailnet>.ts.net/toy/mcp/`
- **传输类型**: Streamable HTTP
- **自定义请求头**:
  - 名称: `X-API-Key`
  - 值: `cat state/api_key.txt`（或你 export 的那个 key）

**各客户端配置入口**：

#### rikkahub（手机 / 桌面）

- 打开 rikkahub → 设置 → MCP 服务器 → 添加服务器
- 名称: `Play toy.`（随便）
- 传输类型: Streamable HTTP
- URL: 见上表
- 请求头: `X-API-Key` = 你的 key

#### Claude Desktop

编辑配置文件（路径按系统）：

| 系统 | 配置路径 |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

加这一段（如果文件已有 `mcpServers` 字段就合并进去）：

```json
{
  "mcpServers": {
    "toy-api": {
      "type": "streamable-http",
      "url": "https://<host>.<your-tailnet>.ts.net/toy/mcp/",
      "headers": {
        "X-API-Key": "你的 key"
      }
    }
  }
}
```

保存后**重启 Claude Desktop**。

#### Cursor

设置 → MCP → "+ Add new global MCP server"，加同样的 JSON 即可。

#### 其他支持 Streamable HTTP 的客户端

填同样的三个字段就行（URL + 类型 + `X-API-Key` 请求头）。

### 5. 手机打开中继页面

手机 Chrome 打开：

- 单服务: `https://<host>.<your-tailnet>.ts.net/relay/`
- 多服务: `https://<host>.<your-tailnet>.ts.net/toy/relay/`

填：
- **VPS URL**:
  - 单服务: `https://<host>.<your-tailnet>.ts.net`
  - 多服务: `https://<host>.<your-tailnet>.ts.net/toy`
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

完整协议见 [docs/sosex-protocol.md](docs/sosex-protocol.md)（含所有 UUID、帧格式、马达控制码、HCI 层抓包特征、Python 参考实现）。原始逆向仓库：[51enuxu/sosexy-ble-control](https://github.com/51enuxu/sosexy-ble-control)。

**关键 UUID**:
- Service: `0000ee01-0000-1000-8000-00805f9b34fb`
- Write Char: `0000ee03-0000-1000-8000-00805f9b34fb`
- Notify Char: `0000ee02-0000-1000-8000-00805f9b34fb`
- 帧格式：12 字节定长（详见协议文档）

### 其他玩具

要支持新玩具：

1. 用 nRF Connect 扫描玩具的 GATT service/characteristic
2. 逆向协议（推荐用官方 App 反编译，参考 [SOSEXY 协议逆向文档](docs/sosex-protocol.md) 作为示例）
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
│   ├── start.sh            # VPS 启动脚本
│   ├── install-mobile.sh   # Android 装依赖 (Termux / Pydroid 通用)
│   └── start-mobile.sh     # Android 启服务 (自动检测 Termux / Pydroid 环境)
├── docs/
│   ├── MCP_CLIENT_SETUP.md # MCP 客户端配置
│   └── sosex-protocol.md   # SOSEXY 玩具 BLE 协议
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

### 鉴权模型（隐私分层设计）

**MCP 鉴权是为隐私。** toy-mcp 用**两层鉴权**守住隐私边界，根据部署模式动态调整作用域：

| 端点 | VPS 模式 | 手机本地模式 | 为什么这样设计 |
|---|---|---|---|
| `/mcp/*` (MCP 客户端接入) | 🔒 需要 `X-API-Key` | 🔓 放行 | MCP 客户端是**用户主动接入**的；VPS 上公网暴露必须锁，手机本地只绑 127.0.0.1 进程间互相受限 |
| `/toy/*` (HTTP 控制：振 / 吸 / 电 / 停) | 🔒 需要 `X-API-Key` | 🔒 **仍需** `X-API-Key` | 这是直接启动玩具的接口，手机上任何 app 都能向 127.0.0.1 发 HTTP，不锁会被恶意调用 |
| `/state` (状态查询) | 🔒 需要 `X-API-Key` | 🔒 **仍需** `X-API-Key` | 会泄漏玩具当前状态 / 使用习惯 |
| `/health` `/relay/*` `/` `/stream` `/manual` | 🔓 放行 | 🔓 放行 | 存活探针 / 静态中继页 / SSE 推送 / 公开文档，不需要鉴权 |

### 为什么控制端点 (`/toy/*` `/state`) 在手机本地也上锁？

Android 沙箱**不隔离 loopback** —— 任何 app 都能向 `127.0.0.1:8765` 发 HTTP 请求。如果控制端点放行，恶意 app 可以偷偷：

- `POST /toy/vibration {"intensity": 100}` → 直接启动玩具
- `GET /state` → 偷看当前玩具状态 / 用户使用习惯

### 隐私边界

- **MCP 客户端** (rikkahub / Claude Desktop / 自家前端) —— 入口受控，是用户主动接入的
- **HTTP 控制端点** —— 任何进程都能调，必须用 API key 守住

> **MCP 鉴权是为隐私；控制端点鉴权也是为隐私。两条线都要，但作用域不同。**

实现细节见 [`src/toy_api.py`](src/toy_api.py) 里的 `APIKeyMiddleware`（中间件层）和 `require_api_key`（路由依赖层）注释。

### 部署安全提醒

- **Tailscale HTTPS**：默认仅 tailnet 内设备可访问
- **不放公网**：不要把 8765 端口直接暴露到公网！如必须，前面套 Caddy / Cloudflare Tunnel 加 HTTPS + 防火墙
- **API key 保密**：`state/api_key.txt` 不要入库，`.gitignore` 已默认排除

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

## 📱 手机本地部署（Android，无需 VPS）

> 没有云服务器？完全 OK。这条路径把 toy-mcp **整套跑在你的 Android 手机里**——不需要 VPS、Tailscale、域名、API Key。
>
> ⚠️ **当前只支持 Android**。iOS 因 Web Bluetooth 限制不支持，详见本节末尾说明。iOS 用户请走 VPS 路径。

### 适用场景

- 不想为玩具控制专门租 VPS
- 玩具和 AI 聊天都在同一台手机上（最常见的本地玩法）
- 想先验证流程再决定要不要上 VPS

### 选哪个？

| 维度 | Termux（推荐） | Pydroid 3 |
|---|---|---|
| Python 包安装 | ✅ 接近 Linux,稳 | ⚠️ PEP 668 偶尔抽风 |
| 学习曲线 | 中（熟悉 `pkg` 即可） | 低（开箱即用） |
| 国内可用性 | ⚠️ **需换源** | ✅ 直接用 |
| 锁屏稳定性 | ✅ `termux-wake-lock` | ⚠️ 需前台服务通知 |
| 适合谁 | 开发者 / 折腾爱好者 | 非开发者 / 想省事 |

**默认推荐 Termux**，尤其国内用户；怕折腾选 Pydroid。

---

### 方案 A：Termux（推荐,国内主流）

#### A.1 装 Termux

> ⚠️ **必须从 F-Droid 装**,Google Play 版已停更,装那个会有各种诡异问题。

🔗 https://f-droid.org/packages/com.termux/

#### A.2 首次初始化

> ⚠️ **国内用户必须先换源** —— 默认源连不上,`pkg update` 直接卡死。

```bash
termux-change-repo                # 选 清华 / 中科大 / 阿里源 任一
pkg update && pkg upgrade -y
pkg install python git curl       # 三个都要装 (Pydroid 自带)
termux-setup-storage              # 给 Termux 访问 sdcard 的权限
```

#### A.3 克隆 + 装依赖

```bash
cd ~/storage/downloads            # Termux 用 storage 路径
git clone https://github.com/tutu-kitty/Toy-Relay-AI-mcp-SOSEXY.git
cd Toy-Relay-AI-mcp-SOSEXY
bash scripts/install-mobile.sh    # 检测到 Termux 会多检查 git / curl
```

#### A.4 启动 + 防杀后台

```bash
termux-wake-lock                  # 关键!防锁屏后 CPU 休眠(SSE 不掉)
bash scripts/start-mobile.sh      # Termux 下自动跑 wake-lock + termux-open-url
```

**然后**(必做):Android 系统设置 → 应用 → **Termux** → 电池 → 选「**不优化**」(或「无限制」)

⚠️ `termux-wake-lock` 是单次有效,每次启动脚本前再跑(或加到 `~/.bashrc`)。

---

### 方案 B：Pydroid 3（开箱即用）

#### B.1 装 Pydroid 3

从 Google Play 装 [Pydroid 3](https://play.google.com/store/apps/details?id=ru.iiec.pydroid3)(免费版即可)。打开后进底部 **Terminal** 标签页。

#### B.2 克隆 + 装依赖

```bash
cd /sdcard/Download               # 或任何可写目录
git clone https://github.com/tutu-kitty/Toy-Relay-AI-mcp-SOSEXY.git
cd Toy-Relay-AI-mcp-SOSEXY
bash scripts/install-mobile.sh
```

`install-mobile.sh` 自动装 `fastapi / uvicorn / mcp`(纯 Python 包,跳过 C 扩展),约 2-3 分钟。

**如果 pip 报错**(Pydroid 常见):

```bash
python -m pip install --prefer-binary --break-system-packages \
    fastapi uvicorn "mcp>=1.0,<2.0"
```

#### B.3 启动

```bash
bash scripts/start-mobile.sh
```

会自动:

1. 后台启 `toy_api.py`,监听 `127.0.0.1:8765`,API key 已禁用
2. 健康检查通过后拉起系统 Chrome
3. 打开 `http://127.0.0.1:8765/relay/`

中继页检测到 localhost → 进入「📱 手机本地模式」,**后端从 DOM 中剥除** VPS URL / API Key 输入框 (不只是 CSS 隐藏)。

---

### 共同步骤（两个方案都适用）

#### 1. 连玩具

中继页 → 切到 **Real 模式** → 点 **🔗 连接 BLE** → 选 `SOSEXY` → 配对。

#### 2. 配置 MCP client（rikkahub）

| 项 | 值 |
|---|---|
| 名称 | 随便（如 `Toy (本地)`） |
| 传输类型 | Streamable HTTP |
| URL | `http://127.0.0.1:8765/mcp/` |
| 请求头 | **不填**（手机本地模式已禁用 API key） |

#### 3. 测试

在 rikkahub 跟 AI 说：

> "把震动设到 50"
> "把吮吸设到 30"
> "停止所有"

玩具应该几乎瞬间响应。

---

### 📱 中继页 DOM 差异（VPS vs 本机）

中继页 (`/relay/chrome_relay.html`) 是按访问来源**后端动态渲染**的。`toy_api.py` 读 `request.client.host`,决定剥哪个 div:

| 访问来源 | `#remote-config` (VPS URL + API Key) | `#local-control` (mobile banner) | 共享控制 (BLE/预设/状态/日志) |
|---|---|---|---|
| 本机 `127.0.0.1` | ❌ 从 DOM 移除 | ✅ 显示 | ✅ 显示 |
| VPS / Tailnet / 公网 | ✅ 显示 | ❌ 从 DOM 移除 | ✅ 显示 |

**为什么不用 CSS `display:none` 藏?**

之前的版本用 JS IIFE 把 input `style.display = 'none'`。两个老问题:

1. **半激活 bug**: IIFE 里任何一行 throw(比如 `$('vps-url').value = ...` 找不到元素),后续 `hideField()` 全跳过。结果: input 视觉上藏了但 DOM 里还在 + value 是空 —— DevTools 看得到空 input,前端 fetch 又报 "请填 VPS URL"。学员当时撞的就是这个。
2. **前端代码永远要写 "input 可能不存在" 的兜底**: 每个 `$(...).value.trim()` 都要先 `if (!el) return;`,非常脏。

改成后端剥 div 之后:
- DevTools 看到的 DOM 就是干净的(本机模式根本没有 VPS URL/API Key 节点)
- 前端 `getBaseUrl()` / `getApiKey()` helper 检测 input 不在 → fallback 到 `location.origin` + 空字符串(本机模式 API key 已禁用)
- 两个老问题同时消失

**自己改模板时的约束**

如果你要往 `#remote-config` 或 `#local-control` 里加新内容,**不要在里面嵌套 `<div>`**。后端用非贪婪正则剥外层 div,如果内层有 `</div>` 会被错切。要嵌套的话用 `<section>` 或 `<span>`。

### ⚠️ 后台保活（关键）

| 方案 | 必做 |
|---|---|
| **Termux** | 跑 `termux-wake-lock` + Android 设置 → Termux → 电池 → 不优化 |
| **Pydroid** | 首次启动允许通知 + Pydroid 设置 → 电池 → 不优化 + 别划掉通知 |

两边共性:**深度休眠会断 BLE** —— 锁屏太久后需要重连。

服务挂了先看 `tail -f logs/api.log` 排查。

### 🔄 跟 VPS 路径的区别

| | Termux 手机本地 | Pydroid 手机本地 | VPS |
|---|---|---|---|
| 需要 VPS | ❌ | ❌ | ✅ |
| 需要 Tailscale / 域名 | ❌ | ❌ | ✅ |
| 需要 API Key | ❌ | ❌ | ✅ |
| 监听地址 | `127.0.0.1` | `127.0.0.1` | `0.0.0.0` |
| 后台保活 | 手动(wake-lock) | 手动(前台通知) | systemd 自动 |
| 跨设备 | ❌ | ❌ | ✅ |
| 锁屏稳定性 | ✅ 较稳 | ⚠️ 偶断 | ✅ 一直稳 |
| Python 包稳定性 | ✅ 接近 Linux | ⚠️ PEP 668 | ✅ 正常 |

两条路径**共用同一份 toy_api.py**——`MOBILE_MODE=1` 环境变量是唯一开关。VPS 部署不设这个变量，行为完全不变。

### 🍎 iOS 用户

iOS 上 Safari 和 Chrome 都是 WKWebView，**不支持 Web Bluetooth**。要走这条路要装 [Bluefy](https://apps.apple.com/app/bluefy-web-ble-browser/id1492822055) 这个第三方浏览器，体验割裂；iOS 后台策略还会冻结 iSH 进程，**基本做不到锁屏后继续玩**。**iOS 用户建议直接走 VPS 路径。**

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

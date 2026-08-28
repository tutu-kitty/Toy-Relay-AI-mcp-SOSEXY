"""
Toy API + MCP (合并版) - 单端口 8765

结构:
  toy_api.py
    ├── FastAPI HTTP API (/state, /toy/suction, ...)
    ├── FastMCP Streamable HTTP (/mcp/*)
    └── Static /relay/* (Chrome 中继页面)

合并原因:
  - 单进程好部署、好监控
  - Tailscale Serve 转发一个端口就够 (toy_api + toy_mcp 共用 8765)
  - 内部调本地函数, 不用 httpx
"""
import json
import secrets
import time
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ---------- 路径 ----------
ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "state" / "state.json"

# ---------- API Key 认证 ----------
# 优先级: 环境变量 > state/api_key.txt > 启动时生成 (并写入文件)
import os
API_KEY_FILE = ROOT / "state" / "api_key.txt"
API_KEY = os.environ.get("TOY_API_KEY")
if not API_KEY and API_KEY_FILE.exists():
    API_KEY = API_KEY_FILE.read_text().strip()
    print(f"🔑 Loaded API key from {API_KEY_FILE}")
if not API_KEY:
    API_KEY = secrets.token_urlsafe(24)
    API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    API_KEY_FILE.write_text(API_KEY)
    print(f"🔑 Generated API key (first run): {API_KEY}")
    print(f"   Saved to {API_KEY_FILE}")
    print(f"   设置环境变量 TOY_API_KEY 可固定使用这个 key")
print(f"🔐 API key: {API_KEY}")


# ---------- Mobile Mode ----------
# 设置 MOBILE_MODE=1 后:
#   - 强制绑定 127.0.0.1 (不暴露给局域网)
#   - 跳过所有 API key 校验 (单设备 localhost 无安全意义)
# 默认关闭, VPS 部署行为完全不变.
MOBILE_MODE = os.environ.get("MOBILE_MODE", "").lower() in ("1", "true", "yes")
if MOBILE_MODE:
    print("📱 Mobile mode: API key disabled, will bind to 127.0.0.1")


# ---------- 全局 API Key 中间件 ----------
class APIKeyMiddleware(BaseHTTPMiddleware):
    """拦截所有非 /relay 路径的请求, 验证 X-API-Key header.

    - 静态文件 /relay/* 放行
    - /health 放行
    - / 放行
    - /stream 放行 (SSE 不能设 header)
    - 其他路径都需要 X-API-Key: <token>
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/relay") or path == "/health" or path == "/" or path == "/stream" or path == "/manual":
            return await call_next(request)
        if MOBILE_MODE:
            # 手机本地模式: 单设备 localhost 无安全意义, 跳过校验
            return await call_next(request)
        key = request.headers.get("X-API-Key", "")
        if not key or key != API_KEY:
            return JSONResponse(
                {"error": "Invalid or missing API key"},
                status_code=401,
            )
        return await call_next(request)

# ========== 状态管理 ==========
def _default_state() -> dict[str, Any]:
    return {
        "cmd": "stop",
        "motor": "all",
        "intensity": 0,
        "updated_at": 0,
        "history": [],
    }


# ========== SSE 订阅 (状态推送, 不依赖轮询) ==========
_state_subscribers: list[asyncio.Queue] = []


def _broadcast_state(state: dict[str, Any]) -> None:
    """同步广播当前 state 到所有 SSE 订阅者"""
    for q in list(_state_subscribers):
        try:
            q.put_nowait(state)
        except asyncio.QueueFull:
            pass
        except Exception:
            pass


def read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _default_state()
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _default_state()


def write_state(new_state: dict[str, Any]) -> dict[str, Any]:
    new_state["updated_at"] = int(time.time() * 1000)
    new_state.setdefault("history", [])
    new_state["history"] = (new_state["history"] + [
        {
            "cmd": new_state.get("cmd"),
            "motor": new_state.get("motor"),
            "intensity": new_state.get("intensity"),
            "ts": new_state["updated_at"],
        }
    ])[-20:]
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)
    # SSE 广播
    _broadcast_state(new_state)
    return new_state


def set_motor(motor: str, intensity: int) -> dict[str, Any]:
    state = read_state()
    state["cmd"] = "set"
    state["motor"] = motor
    state["intensity"] = intensity
    return write_state(state)


def stop_all() -> dict[str, Any]:
    state = read_state()
    state["cmd"] = "stop"
    state["motor"] = "all"
    state["intensity"] = 0
    return write_state(state)


# ========== MCP Server ==========
MOTOR_NAMES_CN = {
    "suction": "吮吸",
    "vibration": "震动",
    "electric": "电流",
}

mcp = FastMCP(
    "toy-control-sosexy",
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)

# 必须先调用 streamable_http_app() 才能创建 session_manager
_mcp_asgi = mcp.streamable_http_app()


def _do_set_motor(motor: str, intensity: int) -> str:
    cn = MOTOR_NAMES_CN.get(motor, motor)
    if not (0 <= intensity <= 100):
        return f"❌ intensity 必须是 0-100, 收到 {intensity}"
    set_motor(motor, intensity)
    if intensity == 0:
        return f"✅ {cn}马达已停止"
    return f"✅ {cn}马达已设到 {intensity}%"


@mcp.tool()
async def toy_suction(intensity: int) -> str:
    """控制玩具的吮吸马达 (吸力)。

    Args:
        intensity: 强度 0-100, 0=停止该马达, 100=最大
    """
    return _do_set_motor("suction", intensity)


@mcp.tool()
async def toy_vibration(intensity: int) -> str:
    """控制玩具的震动马达。

    Args:
        intensity: 强度 0-100, 0=停止该马达, 100=最大
    """
    return _do_set_motor("vibration", intensity)


@mcp.tool()
async def toy_electric(intensity: int) -> str:
    """控制玩具的电流刺激马达。

    Args:
        intensity: 强度 0-100, 0=停止该马达, 100=最大
    """
    return _do_set_motor("electric", intensity)


@mcp.tool()
async def toy_stop() -> str:
    """立即停止玩具所有马达 (吮吸/震动/电流)。"""
    stop_all()
    return "✅ 所有马达已停止"


@mcp.tool()
async def toy_status() -> str:
    """查询玩具当前状态。"""
    state = read_state()
    if state.get("cmd") == "stop":
        return "⏹️ 玩具当前所有马达已停止"
    motor = state.get("motor", "?")
    cn = MOTOR_NAMES_CN.get(motor, motor)
    return (
        f"▶️ 玩具当前状态:\n"
        f"   马达: {cn} ({motor})\n"
        f"   强度: {state.get('intensity')}%\n"
        f"   updated_at: {state.get('updated_at')}"
    )


@mcp.tool()
async def toy_history(limit: int = 5) -> str:
    """查看最近命令历史 (调试用)。

    Args:
        limit: 返回最近几条, 默认 5, 最多 20
    """
    state = read_state()
    history = state.get("history", [])[-limit:]
    if not history:
        return "暂无历史"
    lines = ["📜 最近命令:"]
    for h in history:
        cn = MOTOR_NAMES_CN.get(h.get("motor", ""), h.get("motor", "?"))
        lines.append(
            f"   - ts={h['ts']} cmd={h['cmd']} "
            f"motor={cn} intensity={h['intensity']}"
        )
    return "\n".join(lines)


# ========== FastAPI ==========
class IntensityReq(BaseModel):
    intensity: int = Field(..., ge=0, le=100, description="强度 0-100, 0=停止")


# Auth 依赖: 检查 X-API-Key header
async def require_api_key(request: Request):
    key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not key or key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Set X-API-Key header.",
        )
    return key


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 启动 MCP session manager (TaskGroup)
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Toy API + MCP", version="0.4.0", lifespan=lifespan)
app.add_middleware(APIKeyMiddleware)

# Mount MCP Streamable HTTP
app.mount("/mcp", _mcp_asgi)


# ========== SSE 推送 (不依赖轮询) ==========
@app.get("/stream")
async def stream():
    """SSE 端点 - 主动推送 state 变化. Chrome 中继页用 EventSource 订阅.

    不需要 auth (SSE/EventSource 协议不能设 header). 只暴露 toy 控制状态.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    async def event_gen():
        _state_subscribers.append(queue)
        try:
            yield f"data: {json.dumps(read_state(), ensure_ascii=False)}\n\n"
            while True:
                state = await queue.get()
                yield f"data: {json.dumps(state, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            try:
                _state_subscribers.remove(queue)
            except ValueError:
                pass

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/")
async def root():
    return {
        "service": "toy-api-mcp",
        "version": "0.4.0",
        "endpoints": [
            "/state", "/toy/status",
            "/toy/suction", "/toy/vibration", "/toy/electric", "/toy/stop",
            "/mcp", "/relay/",
        ],
    }


@app.get("/health")
async def health():
    return {"ok": True, "ts": int(time.time() * 1000)}


@app.get("/state", dependencies=[Depends(require_api_key)])
async def get_state():
    return read_state()


@app.get("/toy/status", dependencies=[Depends(require_api_key)])
async def toy_status_http():
    return read_state()


@app.post("/toy/suction", dependencies=[Depends(require_api_key)])
async def toy_suction_http(req: IntensityReq):
    return {"ok": True, "state": set_motor("suction", req.intensity)}


@app.post("/toy/vibration", dependencies=[Depends(require_api_key)])
async def toy_vibration_http(req: IntensityReq):
    return {"ok": True, "state": set_motor("vibration", req.intensity)}


@app.post("/toy/electric", dependencies=[Depends(require_api_key)])
async def toy_electric_http(req: IntensityReq):
    return {"ok": True, "state": set_motor("electric", req.intensity)}


@app.post("/toy/stop", dependencies=[Depends(require_api_key)])
async def toy_stop_http():
    return {"ok": True, "state": stop_all()}


# 静态文件: Chrome 中继页面
WEB_DIR = ROOT / "web"
if WEB_DIR.exists():
    app.mount("/relay", StaticFiles(directory=str(WEB_DIR), html=True), name="relay")


# 手动手册 (markdown, 文本响应)
@app.get("/manual", include_in_schema=False)
async def manual():
    """返回操作手册 markdown"""
    manual_path = ROOT / "OPERATION_MANUAL.md"
    if not manual_path.exists():
        return PlainTextResponse("# 操作手册未找到\n\n请联系管理员。", media_type="text/markdown; charset=utf-8")
    return PlainTextResponse(
        manual_path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
    )


if __name__ == "__main__":
    import uvicorn
    host = "127.0.0.1" if MOBILE_MODE else "0.0.0.0"
    uvicorn.run(app, host=host, port=8765, log_level="info")
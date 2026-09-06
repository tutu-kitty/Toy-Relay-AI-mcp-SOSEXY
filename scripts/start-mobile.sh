#!/usr/bin/env bash
# Toy MCP - 手机端启动 (Android Pydroid 3 / Termux)
#
# 用法: bash scripts/start-mobile.sh
#
# 会:
#   1. 启 toy_api.py @ 127.0.0.1:8765 (MOBILE_MODE=1, 跳过 API key, 不绑外网)
#   2. 等健康检查通过
#   3. 自动拉起 Chrome 打开 http://127.0.0.1:8765/relay/
#   4. 把 PID 写到 logs/api.pid, 后续可 kill 停

set -e

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
LOG_DIR="$(pwd)/logs"
mkdir -p "$LOG_DIR"

echo "📱 Toy MCP 手机端启动"
echo "======================"
echo ""

# ---- 前置检查 ----

if [ ! -f "src/toy_api.py" ]; then
    echo "❌ src/toy_api.py 不存在, 请在 toy-mcp 仓库根目录运行此脚本"
    exit 1
fi

if ! command -v "$PYTHON" > /dev/null 2>&1; then
    if command -v python > /dev/null 2>&1; then
        PYTHON="python"
    else
        echo "❌ 找不到 python / python3, 请用 Pydroid 3 或 Termux 内置终端"
        exit 1
    fi
fi

# 校验依赖
if ! $PYTHON -c "import fastapi, uvicorn, mcp" 2>/dev/null; then
    echo "❌ 依赖未装, 请先跑: bash scripts/install-mobile.sh"
    exit 1
fi

# ---- Termux: 启 wake-lock + curl 检查 ----
if [ -d "/data/data/com.termux" ]; then
    if ! command -v curl > /dev/null 2>&1; then
        echo "❌ Termux 缺 curl(健康检查要用)"
        echo "   请跑: pkg install curl"
        exit 1
    fi
    if command -v termux-wake-lock > /dev/null 2>&1; then
        echo "🔒 Termux wake-lock(防锁屏休眠)..."
        termux-wake-lock || echo "   ⚠️  wake-lock 没起来, toy-mcp 锁屏后可能被系统杀"
        echo ""
    else
        echo "⚠️  没找到 termux-wake-lock,跳过(锁屏后 toy-mcp 会被杀)"
        echo ""
    fi
fi

# ---- 停旧进程 ----

if [ -f "$LOG_DIR/api.pid" ]; then
    OLD_PID=$(cat "$LOG_DIR/api.pid")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⏹  停旧进程 (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
        # 还活着就强杀
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill -9 "$OLD_PID" 2>/dev/null || true
        fi
    fi
    rm -f "$LOG_DIR/api.pid"
fi

# ---- 启动服务 ----

echo "🚀 启动 toy-mcp (MOBILE_MODE=1, 监听 127.0.0.1:8765)..."
echo "   日志: $LOG_DIR/api.log"
echo ""

MOBILE_MODE=1 PYTHONPATH="$(pwd)/src" \
    nohup "$PYTHON" src/toy_api.py > "$LOG_DIR/api.log" 2>&1 &
PID=$!
echo $PID > "$LOG_DIR/api.pid"

# 等服务起来 (Android 上 cold start 可能慢一点)
sleep 4

# 健康检查
HEALTH_OK=0
for i in 1 2 3 4 5; do
    if curl -sf http://127.0.0.1:8765/health > /dev/null 2>&1; then
        HEALTH_OK=1
        break
    fi
    sleep 2
done

if [ "$HEALTH_OK" != "1" ]; then
    echo ""
    echo "❌ 服务起不来, 日志最后几行:"
    echo "----------------------------"
    tail -n 20 "$LOG_DIR/api.log"
    echo "----------------------------"
    echo ""
    echo "排查: tail -f logs/api.log"
    exit 1
fi

echo "✅ 服务已起 (PID: $PID)"
echo "   health: $(curl -s http://127.0.0.1:8765/health)"
echo ""

# ---- 拉起 Chrome 打开中继页 ----

RELAY_URL="http://127.0.0.1:8765/relay/"

if [ -d "/data/data/com.termux" ] && command -v termux-open-url > /dev/null 2>&1; then
    # Termux: termux-open-url 更稳(选默认浏览器)
    echo "🌐 打开浏览器..."
    if termux-open-url "$RELAY_URL" 2>/dev/null; then
        echo "   ✓ 浏览器已拉起"
    else
        echo "   ⚠️  浏览器没拉起来, 手动打开: $RELAY_URL"
    fi
elif command -v am > /dev/null 2>&1; then
    # Pydroid 终端 / 其他 Android 环境
    echo "🌐 打开 Chrome 中继页..."
    if am start -a android.intent.action.VIEW -d "$RELAY_URL" > /dev/null 2>&1; then
        echo "   ✓ Chrome 已拉起"
    else
        echo "   ⚠️  Chrome 没拉起来, 手动打开: $RELAY_URL"
    fi
else
    echo "🌐 浏览器手动打开: $RELAY_URL"
fi

echo ""
echo "📋 rikkahub MCP 配置:"
echo "   URL: $RELAY_URL 里的 mcp/ (即 http://127.0.0.1:8765/mcp/)"
echo "   X-API-Key: 不用填 (手机本地模式已禁用)"
echo "   传输: Streamable HTTP"
echo ""
echo "🛑 停服务: kill \$(cat logs/api.pid)"
echo "📄 看日志: tail -f logs/api.log"

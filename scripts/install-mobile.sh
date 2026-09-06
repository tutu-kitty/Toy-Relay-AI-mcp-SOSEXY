#!/usr/bin/env bash
# Toy MCP - 手机端依赖安装 (Android Pydroid 3 / Termux 专用)
#
# 只装纯 Python 包, 跳过 uvloop / orjson 这类 C 扩展
# (手机上没编译器, 装 C 扩展会失败)
#
# 用法: bash scripts/install-mobile.sh

set -e

cd "$(dirname "$0")/.."

echo "📱 Toy MCP 手机端依赖安装"
echo "============================"
echo ""

# 检查 python3
if ! command -v python3 > /dev/null 2>&1 && ! command -v python > /dev/null 2>&1; then
    echo "❌ 找不到 python / python3"
    echo ""
    echo "请先装 Pydroid 3 (Play Store) 或 Termux (F-Droid),"
    echo "然后用它们内置的终端跑这个脚本."
    exit 1
fi

PYTHON="$(command -v python3 || command -v python)"

echo "🔧 Python: $($PYTHON --version) @ $(which $PYTHON)"
echo ""

# ---- 检测 Termux 环境 ----
IS_TERMUX=0
if [ -d "/data/data/com.termux" ]; then
    IS_TERMUX=1
    echo "📱 检测到 Termux 环境"
    echo ""

    # Termux 必装 git (本脚本要在 git 仓库里跑,且 git clone 是用户前置步骤)
    if ! command -v git > /dev/null 2>&1; then
        echo "❌ Termux 缺 git"
        echo ""
        echo "请先跑:"
        echo "  pkg install git"
        echo ""
        echo "国内用户先换源:termux-change-repo → 选清华 / 中科大 / 阿里"
        exit 1
    fi

    # 提示 storage 没设
    if [ ! -d "$HOME/storage" ]; then
        echo "⚠️  没看到 ~/storage,Termux 还没访问 sdcard"
        echo "   跑一次: termux-setup-storage"
        echo ""
    fi
fi

# 升级 pip (Pydroid 自带 pip 但版本可能旧)
echo "⏫ 升级 pip..."
$PYTHON -m pip install --upgrade pip --quiet 2>&1 | tail -3 || true
echo ""

# 装最小依赖集 (纯 Python + ARM 预编译 wheel)
echo "📦 安装依赖 (fastapi / uvicorn / mcp)..."
echo "   注意: 用 --prefer-binary 避免源码编译"
echo ""

# 显式装这三个, mcp 会拉 pydantic / httpx / starlette / anyio 等依赖
$PYTHON -m pip install --prefer-binary --quiet \
    "fastapi" \
    "uvicorn" \
    "mcp>=1.0,<2.0"

echo ""
echo "✅ 验证依赖..."

$PYTHON -c "
import sys
mods = ['fastapi', 'uvicorn', 'mcp', 'pydantic', 'starlette', 'anyio', 'httpx']
failed = []
for m in mods:
    try:
        __import__(m)
        print(f'  ✓ {m}')
    except ImportError:
        print(f'  ✗ {m} (导入失败)')
        failed.append(m)
if failed:
    print()
    print(f'❌ {len(failed)} 个模块导入失败:', failed)
    sys.exit(1)
"

echo ""
echo "🎉 依赖装好了!"
echo ""
echo "下一步: bash scripts/start-mobile.sh"
echo ""
echo "⚠️  Pydroid 提示:"
echo "   - 首次启动会弹通知权限, 必须允许 (后台保活用)"
echo "   - 把 Pydroid 加到电池优化白名单"
echo "   - 别划掉 Pydroid 的前台服务通知"

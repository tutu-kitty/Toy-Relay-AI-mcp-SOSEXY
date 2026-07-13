#!/usr/bin/env bash
# Toy API + MCP 启动脚本 - 单进程 (合并版)
set -e
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
LOG_DIR="$(pwd)/logs"
mkdir -p "$LOG_DIR"

# 停掉之前的
for f in api.pid mcp.pid; do
  if [ -f "$LOG_DIR/$f" ]; then
    PID=$(cat "$LOG_DIR/$f")
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID" 2>/dev/null || true
    fi
  fi
done
sleep 1

# 起合并后的 toy_api.py @ 8765 (内含 MCP + 静态文件)
echo '[+] Starting Toy API + MCP @ :8765'
PYTHONPATH="$(pwd)/src" nohup "$PYTHON" src/toy_api.py > "$LOG_DIR/api.log" 2>&1 &
echo $! > "$LOG_DIR/api.pid"

sleep 3
echo
echo '----- log -----'
tail -n 15 "$LOG_DIR/api.log"
echo
echo '----- health check -----'
if curl -sf http://127.0.0.1:8765/health > /dev/null; then
  echo '[OK] HTTP API is running'
else
  echo '[FAIL] HTTP API is not responding'
fi
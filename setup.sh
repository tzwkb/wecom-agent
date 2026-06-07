#!/bin/bash
# WeCom Agent Skill + MCP Server — macOS installer
# Usage: bash setup.sh
set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ "$(uname)" != "Darwin" ]]; then
    echo "此脚本仅适用于 macOS。"
    exit 1
fi

echo "=== WeCom Agent 安装 (macOS) ==="
echo "目录: $SKILL_DIR"
echo ""

PYTHON="/opt/homebrew/bin/python3"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"
echo "[1/3] 使用全局 Python: $PYTHON ($("$PYTHON" --version))"

echo "[2/3] 安装 Python 依赖(全局)..."
"$PYTHON" -m pip install --break-system-packages --quiet \
    mcp frida-tools cryptography requests 2>&1 | tail -1
# 文档解析(openfile)/语音转写按需:openpyxl pdfplumber python-docx pilk faster-whisper
"$PYTHON" -c "import mcp; print('  mcp OK')" 2>/dev/null || {
    echo "  [!] 安装失败,手动: $PYTHON -m pip install --break-system-packages mcp"
}

echo "[3/3] 注册 MCP Server (wecom)..."
if command -v claude &>/dev/null; then
    claude mcp remove wecom -s user 2>/dev/null || true
    claude mcp add -s user wecom \
        "$PYTHON" \
        "$SKILL_DIR/server.py" 2>&1
    echo "  MCP 已注册"
else
    echo "  Claude Code 未安装,跳过"
fi

echo ""
echo "=== 安装完成 ==="
echo ""
echo "后续步骤:"
echo "  1. 提 key + 解密: python3 decrypt/macos/read_wecom.py (扫 key→解密→导出)"
echo "  2. 重启 Claude Code → MCP 工具 wecom_* 可用"
echo "  3. 不用 MCP 也行: python3 decrypt/macos/wecom_local.py <子命令> [--json]"

#!/usr/bin/env bash
# release/build.sh — LLM Router Release 构建脚本
#
# 用法:
#   bash release/build.sh              # 构建前端 + Tauri
#   bash release/build.sh --python     # 先用 PyInstaller 打包后端再构建 Tauri
#
# 产出:
#   release/llm-router/ 目录包含完整的可分发产物

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE_DIR="$ROOT/release/llm-router"

echo "=== LLM Router Release Build ==="
echo "Root: $ROOT"
echo "Release: $RELEASE_DIR"

# 清理上次 release
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# ----------------------------------
# 1. 前端构建
# ----------------------------------
echo ""
echo "[1/3] Building frontend..."
cd "$ROOT/frontend"
npm run build

# 复制前端产物
mkdir -p "$RELEASE_DIR/frontend"
cp -r dist "$RELEASE_DIR/frontend/"
echo "  frontend/dist → release/llm-router/frontend/dist"

# ----------------------------------
# 2. Python 后端（可选 PyInstaller）
# ----------------------------------
if [[ "${1:-}" == "--python" ]]; then
    echo ""
    echo "[2/3] Packaging Python backend with PyInstaller..."
    cd "$ROOT"
    # 使用 backend/src/server.py 作为入口
    python -m PyInstaller \
        --name "llm-router-backend" \
        --onedir \
        --console \
        --add-data "backend:backend" \
        --add-data "src:src" \
        --hidden-import "uvicorn.logging" \
        --hidden-import "uvicorn.loops.auto" \
        --hidden-import "fastapi" \
        --hidden-import "aiosqlite" \
        --hidden-import "aiohttp" \
        --hidden-import "yaml" \
        --hidden-import "cryptography" \
        --hidden-import "jsonschema" \
        --exclude-module "nicegui" \
        --exclude-module "pystray" \
        --exclude-module "PIL" \
        --exclude-module "torch" \
        --exclude-module "numpy" \
        --exclude-module "pandas" \
        backend/src/server.py

    cp -r dist/llm-router-backend "$RELEASE_DIR/backend/"
    echo "  backend packaged → release/llm-router/backend/"
else
    echo ""
    echo "[2/3] Skipping Python packaging (use --python to package backend)."
    echo "  Copying backend source instead..."
    mkdir -p "$RELEASE_DIR/backend"
    cp -r "$ROOT/backend/." "$RELEASE_DIR/backend/"
    cp -r "$ROOT/src" "$RELEASE_DIR/"
    cp "$ROOT/pyproject.toml" "$RELEASE_DIR/"
    # 清理 __pycache__ 和残留旧文件
    find "$RELEASE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    rm -rf "$RELEASE_DIR/src/gui" 2>/dev/null || true
    rm -rf "$RELEASE_DIR/src/llm_router.egg-info" 2>/dev/null || true
fi

# ----------------------------------
# 3. Tauri 构建
# ----------------------------------
echo ""
echo "[3/3] Building Tauri desktop app..."
cd "$ROOT"
# 必须用 tauri build（而非 cargo build），否则前端 dist 不会嵌入 exe，
# 运行时 webview 加载不到资源 → "localhost 拒绝连接"。
if command -v npx &>/dev/null; then
    npx --prefix frontend tauri build 2>&1 | tail -10
    if [ -f "src-tauri/target/release/llm-router.exe" ]; then
        cp "src-tauri/target/release/llm-router.exe" "$RELEASE_DIR/"
        echo "  llm-router.exe → release/llm-router/"
    elif [ -f "src-tauri/target/release/llm-router" ]; then
        cp "src-tauri/target/release/llm-router" "$RELEASE_DIR/"
        echo "  llm-router → release/llm-router/"
    else
        echo "  WARNING: Tauri binary not found in src-tauri/target/release/"
    fi
else
    echo "  WARNING: npx not found, skipping Tauri build."
    echo "  Install Node.js: https://nodejs.org"
fi

echo ""
echo "=== Build Complete ==="
echo "Release directory: $RELEASE_DIR"
echo "Files:"
find "$RELEASE_DIR" -type f | sort | sed 's|'"$RELEASE_DIR"'|  |'

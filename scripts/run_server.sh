#!/bin/bash

# GraphRAG API服務啟動腳本

echo "🚀 啟動 GraphRAG API 服務..."
echo "📊 服務信息:"
echo "  - API地址: http://localhost:8000"
echo "  - 文檔地址: http://localhost:8000/docs"
echo ""

# 檢查Python環境 (優先使用uv)
if command -v uv &> /dev/null; then
    echo "📦 使用 uv 啟動服務..."
    uv run uvicorn grag.api.app:app --host 0.0.0.0 --port 8000 --reload
elif command -v python3 &> /dev/null; then
    echo "🐍 使用 python3 啟動服務..."
    python3 -m uvicorn grag.api.app:app --host 0.0.0.0 --port 8000 --reload
else
    echo "❌ 未找到 uv 或 python3，請確保已安裝"
    exit 1
fi

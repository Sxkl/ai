#!/bin/bash
# api-v4-auto-fix 部署脚本
# 用法: ./deploy.sh [--init-db] [--seed] [--run]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  api-v4-auto-fix Agent 集群部署"
echo "=========================================="
echo ""

# ============================================================
# Step 1: 安装依赖
# ============================================================
if [ "$1" == "--init-db" ] || [ "$1" == "--all" ]; then
    echo "📦 安装 Python 依赖..."
    pip install chromadb sentence-transformers pyyaml requests 2>/dev/null || \
    pip3 install chromadb sentence-transformers pyyaml requests
    echo "✅ 依赖安装完成"
fi

# ============================================================
# Step 2: 初始化 ChromaDB
# ============================================================
if [ "$1" == "--init-db" ] || [ "$1" == "--all" ]; then
    echo ""
    echo "🗄️  初始化 ChromaDB..."
    cd chromadb
    python init_db.py
    cd ..
    echo "✅ ChromaDB 初始化完成"
fi

# ============================================================
# Step 3: 种子写入已知模式
# ============================================================
if [ "$1" == "--seed" ] || [ "$1" == "--all" ]; then
    echo ""
    echo "🌱 写入已知问题模式..."
    cd chromadb
    python seed_patterns.py
    cd ..
    echo "✅ 种子数据写入完成"
fi

# ============================================================
# Step 4: 验证
# ============================================================
if [ "$1" == "--verify" ] || [ "$1" == "--all" ]; then
    echo ""
    echo "🔍 验证 ChromaDB 数据..."
    cd chromadb
    python query.py "Connection refused gateway Feign" --collection error_patterns --top-k 3
    cd ..
    echo ""
    echo "✅ 验证完成"
fi

echo ""
echo "=========================================="
echo "  部署完成! 运行方式:"
echo "  ./deploy.sh --all        # 完整初始化"
echo "  ./deploy.sh --init-db    # 仅安装依赖+初始化DB"
echo "  ./deploy.sh --seed       # 仅写入种子数据"
echo "  ./deploy.sh --verify     # 验证查询"
echo "=========================================="

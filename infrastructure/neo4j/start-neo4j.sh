#!/bin/bash

# Neo4j快速啟動腳本
# 用法: ./start-neo4j.sh

set -e  # 遇到錯誤立即退出

echo "🐳 GRAG Neo4j Docker 啟動腳本"
echo "================================="

# 檢查Docker是否運行
echo "1. 檢查Docker daemon..."
if ! docker version > /dev/null 2>&1; then
    echo "❌ Docker daemon未運行。請先啟動Docker Desktop。"
    echo "   Mac: 開啟Docker Desktop應用程式"
    echo "   Linux: sudo systemctl start docker"
    exit 1
fi

echo "✅ Docker 可以連接"

# 停止現有Neo4j容器（如果存在的話）
echo "2. 清理舊的Neo4j容器..."
docker compose down -v 2>/dev/null || docker-compose down -v 2>/dev/null || true
docker stop neo4j-grag 2>/dev/null || true
docker rm neo4j-grag 2>/dev/null || true

echo "3. 啟動Neo4j容器..."
docker compose up -d neo4j || docker-compose up -d neo4j

echo "4. 等待Neo4j啟動..."
echo "   (這需要約30-60秒，請稍候)"

# 等待Neo4j啟動
max_attempts=60
attempts=0

while [ $attempts -lt $max_attempts ]; do
    if docker compose exec -T neo4j cypher-shell -u neo4j -p testpass123 "MATCH () RETURN count(*) limit 1" 2>/dev/null ||
       docker-compose exec -T neo4j cypher-shell -u neo4j -p testpass123 "MATCH () RETURN count(*) limit 1" 2>/dev/null; then
        echo "✅ Neo4j 已成功啟動！"
        break
    fi

    attempts=$((attempts + 1))
    echo -n "."
    sleep 2
done

if [ $attempts -eq $max_attempts ]; then
    echo "❌ Neo4j啟動超時"
    echo "檢查日誌:"
    docker compose logs neo4j 2>/dev/null || docker-compose logs neo4j 2>/dev/null
    exit 1
fi

echo ""
echo "🎉 Neo4j已準備就緒！"
echo ""
echo "連線資訊:"
echo "  🌐 網頁介面: http://localhost:7474"
echo "  🔗 資料庫URI: neo4j://localhost:7687"
echo "  👤 用戶名: neo4j"
echo "  🔑 密碼: testpass123"
echo ""
echo "測試連線:"
echo "  python -c \"from neo4j import GraphDatabase; driver=GraphDatabase.driver('neo4j://localhost:7687', auth=('neo4j', 'testpass123')); driver.close(); print('✅ 連線成功')\""
echo ""
echo "停止Neo4j:"
echo "  docker compose down || docker-compose down"
echo ""
echo "現在你可以。"
echo "1. 在瀏覽器訪問 http://localhost:7474 查看Neo4j"
echo "2. 更新專案的 .env 文件的Neo4j設定"
echo "3. 測試完整的GUI功能"

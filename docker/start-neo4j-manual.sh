#!/bin/bash

# Neo4j手動啟動腳本（不依賴docker-compose）
# 用法: ./start-neo4j-manual.sh

set -e

echo "🐳 Neo4j手動啟動腳本"
echo "====================="

# 檢查Docker
echo "1. 檢查Docker狀態..."
if ! docker version > /dev/null 2>&1; then
    echo "❌ Docker未運行。請先啟動Docker Desktop。"
    exit 1
fi

echo "✅ Docker可以連接"

# 清理舊容器
echo "2. 清理舊Neo4j容器..."
docker stop neo4j-grag 2>/dev/null || true
docker rm neo4j-grag 2>/dev/null || true

echo "3. 啟動Neo4j容器..."
docker run \
    --name neo4j-grag \
    -p7474:7474 -p7687:7687 \
    -d \
    --env NEO4J_AUTH=neo4j/testpass123 \
    --env NEO4J_PLUGINS='["graph-data-science"]' \
    neo4j

echo "4. 等待Neo4j啟動..."
echo "   (會自動測試連線，每秒檢查一次)"

# 等待啟動
max_attempts=60
attempts=0

while [ $attempts -lt $max_attempts ]; do
    if docker exec neo4j-grag cypher-shell -u neo4j -p testpass123 "MATCH () RETURN count(*) limit 1" > /dev/null 2>&1; then
        echo "✅ Neo4j已成功啟動！"
        break
    fi

    attempts=$((attempts + 1))
    echo -n "."
    sleep 2
done

if [ $attempts -eq $max_attempts ]; then
    echo "❌ Neo4j啟動超時"
    echo "檢查日誌: docker logs neo4j-grag"
    docker logs neo4j-grag | tail -20
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
echo "  docker exec neo4j-grag cypher-shell -u neo4j -p testpass123 'MATCH () RETURN count(*) limit 1;'"
echo ""
echo "停止Neo4j:"
echo "  docker stop neo4j-grag"

#!/usr/bin/env python3
"""
直接測試向量搜索功能
"""

import asyncio
import os
import sys
import pytest
from supabase import create_client

@pytest.mark.asyncio
async def test_vector_search():
    try:
        # 從.env文件讀取Supabase設置
        env_file = '.env'
        supabase_url = None
        supabase_key = None

        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('SUPABASE_URL='):
                        supabase_url = line.split('=', 1)[1]
                    elif line.startswith('SUPABASE_KEY='):
                        supabase_key = line.split('=', 1)[1]

        supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        supabase_key = supabase_key or os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            print("❌ 無法獲取 SUPABASE_URL 或 SUPABASE_KEY")
            return

        print(f"🔗 連接Supabase: {supabase_url}")

        # 創建Supabase客戶端
        supabase = create_client(supabase_url, supabase_key)

        # 測試1: 檢查向量數據
        print("\n📊 測試1: 檢查向量數據")
        response = supabase.table('vectors').select('*').limit(3).execute()
        print(f"✅ 獲取到 {len(response.data)} 條向量記錄")

        if response.data:
            for i, record in enumerate(response.data):
                embedding = record.get('embedding', [])
                print(f"  記錄 {i+1}: vector_id={record.get('vector_id')}, type={record.get('type')}, embedding_length={len(embedding)}")
                if len(embedding) > 0:
                    print(f"    嵌入樣本: {embedding[:5]}...")

        # 測試2: 直接相似度計算
        print("\n🔍 測試2: 直接相似度計算")
        import numpy as np
        from sentence_transformers import SentenceTransformer

        # 加載embedding模型
        model = SentenceTransformer('all-MiniLM-L6-v2')

        # 生成測試查詢的嵌入
        test_query = "510(k)"
        query_embedding = model.encode(test_query)
        print(f"查詢 '{test_query}' 的嵌入長度: {len(query_embedding)}")

        # 獲取所有向量並計算相似度
        all_vectors = supabase.table('vectors').select('*').execute()

        similarities = []
        query_vec = np.array(query_embedding)

        for record in all_vectors.data:
            db_embedding = np.array(record['embedding'])

            # 確保向量長度匹配
            if len(db_embedding) != len(query_vec):
                print(f"⚠️ 向量長度不匹配: 查詢={len(query_vec)}, 數據庫={len(db_embedding)}")
                continue

            # 計算餘弦相似度
            similarity = np.dot(query_vec, db_embedding) / (np.linalg.norm(query_vec) * np.linalg.norm(db_embedding))
            similarities.append((similarity, record))

        # 排序並顯示top結果
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_results = similarities[:3]

        print(f"相似度計算結果 (top 3):")
        for i, (sim, record) in enumerate(top_results):
            print(".3f")

        # 測試3: 檢查是否有很高相似度的結果
        high_similarity = [s for s, r in similarities if s > 0.5]
        print(f"高相似度結果 (>0.5): {len(high_similarity)} 個")

    except Exception as e:
        print(f"❌ 向量搜索測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vector_search())

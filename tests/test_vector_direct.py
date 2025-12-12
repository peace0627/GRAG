#!/usr/bin/env python3
"""
直接測試向量搜索邏輯
"""

import asyncio
import os
import sys
import numpy as np
from supabase import create_client

async def test_vector_search_direct():
    try:
        # 從.env文件讀取Supabase設置
        env_file = '.env'
        supabase_url = None
        supabase_key = None

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

        print("🔗 連接Supabase...")
        supabase = create_client(supabase_url, supabase_key)

        # 測試1: 檢查向量數據
        print("\n📊 測試1: 檢查向量數據")
        response = supabase.table('vectors').select('*').limit(5).execute()
        print(f"✅ 獲取到 {len(response.data)} 條向量記錄")

        if response.data:
            for i, record in enumerate(response.data):
                embedding = record.get('embedding', [])
                print(f"  記錄 {i+1}: vector_id={record.get('vector_id')[:8]}..., type={record.get('type')}, embedding_length={len(embedding)}")
                if len(embedding) > 0:
                    print(f"    嵌入樣本: {embedding[:3]}...")

        # 測試2: 直接相似度計算
        print("\n🔍 測試2: 直接相似度計算")

        # 生成測試查詢的嵌入
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        test_query = "510(k)"
        query_embedding = model.encode(test_query)
        print(f"查詢 '{test_query}' 的嵌入長度: {len(query_embedding)}")
        print(f"查詢嵌入樣本: {query_embedding[:3]}")

        # 獲取所有向量並計算相似度
        all_vectors = supabase.table('vectors').select('*').execute()
        print(f"數據庫中有 {len(all_vectors.data)} 條向量記錄")

        similarities = []
        query_vec = np.array(query_embedding)

        for record in all_vectors.data:
            # 處理JSONB數據 - 可能是字符串或列表
            embedding_data = record['embedding']
            if isinstance(embedding_data, str):
                # 如果是字符串，嘗試解析JSON
                import json
                try:
                    embedding_data = json.loads(embedding_data)
                except:
                    print(f"⚠️ 無法解析向量字符串: {embedding_data[:50]}...")
                    continue

            db_embedding = np.array(embedding_data)

            # 檢查向量長度
            if len(db_embedding) != len(query_vec):
                print(f"⚠️ 向量長度不匹配: 查詢={len(query_vec)}, 數據庫={len(db_embedding)}")
                continue

            # 計算餘弦相似度
            similarity = np.dot(query_vec, db_embedding) / (np.linalg.norm(query_vec) * np.linalg.norm(db_embedding))
            similarities.append((similarity, record))

            print(".3f")

        # 排序並顯示top結果
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_results = similarities[:3]

        print("\n相似度計算結果 (top 3):")
        for i, (sim, record) in enumerate(top_results):
            print(".3f")
            if sim > 0.1:  # 如果有相似度>0.1，顯示內容
                # 嘗試獲取chunk內容
                chunk_id = record.get('chunk_id')
                if chunk_id:
                    print(f"      內容: {record.get('content_preview', 'No preview')[:100]}...")

        # 測試3: 檢查是否有很高相似度的結果
        high_similarity = [s for s, r in similarities if s > 0.1]
        print(f"\n📈 高相似度結果 (>0.1): {len(high_similarity)} 個")

        if len(high_similarity) == 0:
            print("❌ 沒有找到任何相似度>0.1的結果！")

            # 檢查相似度分佈
            all_similarities = [s for s, r in similarities]
            print(f"相似度範圍: {min(all_similarities):.3f} - {max(all_similarities):.3f}")
            print(f"相似度平均值: {np.mean(all_similarities):.3f}")

    except Exception as e:
        print(f"❌ 向量搜索測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vector_search_direct())

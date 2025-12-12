#!/usr/bin/env python3
"""
測試Supabase向量存儲和查詢
"""

import os
import sys
import asyncio
from supabase import create_client

async def test_supabase():
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

        # 如果環境變數存在，使用環境變數
        supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        supabase_key = supabase_key or os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            print("❌ 無法獲取 SUPABASE_URL 或 SUPABASE_KEY")
            return

        print(f"🔗 連接Supabase: {supabase_url}")

        # 創建Supabase客戶端
        supabase = create_client(supabase_url, supabase_key)

        # 測試1: 檢查vectors表是否存在
        print("\n📋 測試1: 檢查vectors表")
        try:
            response = supabase.table('vectors').select('count', count='exact').limit(1).execute()
            print(f"✅ vectors表存在，記錄數: {response.count}")
        except Exception as e:
            print(f"❌ vectors表不存在或權限錯誤: {e}")
            return

        # 測試2: 檢查是否有向量數據
        print("\n📊 測試2: 檢查向量數據")
        try:
            response = supabase.table('vectors').select('*').limit(5).execute()
            print(f"✅ 獲取到 {len(response.data)} 條向量記錄")
            if response.data:
                for i, record in enumerate(response.data[:2]):
                    print(f"  記錄 {i+1}: vector_id={record.get('vector_id')}, type={record.get('type')}")
        except Exception as e:
            print(f"❌ 無法獲取向量數據: {e}")

        # 測試3: 嘗試插入測試向量
        print("\n💾 測試3: 插入測試向量")
        try:
            test_embedding = [0.1] * 384  # 384維測試向量
            test_record = {
                'embedding': test_embedding,
                'document_id': 'test-doc-123',
                'type': 'chunk',
                'page': 1,
                'order': 0
            }

            response = supabase.table('vectors').insert(test_record).execute()
            if response.data:
                print(f"✅ 成功插入測試向量: {response.data[0].get('vector_id')}")
            else:
                print(f"❌ 插入測試向量失敗: {response}")
        except Exception as e:
            print(f"❌ 插入測試向量失敗: {e}")

    except Exception as e:
        print(f"❌ Supabase測試失敗: {e}")

if __name__ == "__main__":
    asyncio.run(test_supabase())

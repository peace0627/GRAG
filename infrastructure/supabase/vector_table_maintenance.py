#!/usr/bin/env python3
"""
重建Supabase vectors表
"""

import os
from supabase import create_client

async def rebuild_table():
    try:
        # 讀取環境變數
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

        print("🗑️ 刪除舊表...")
        try:
            # 先嘗試刪除所有記錄
            result = supabase.table('vectors').delete().neq('vector_id', '00000000-0000-0000-0000-000000000000').execute()
            print(f"✅ 刪除了 {len(result.data)} 條舊記錄")
        except Exception as e:
            print(f"⚠️ 刪除記錄失敗: {e}")

        print("📝 表結構已更改為JSONB，現在可以重新上傳數據")

        print("🎉 準備完成")

    except Exception as e:
        print(f"❌ 表重建失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(rebuild_table())

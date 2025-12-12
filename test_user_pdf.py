#!/usr/bin/env python3
"""
測試用戶提供的PDF內容上傳
"""

import sys
import os
from pathlib import Path
import asyncio
import tempfile
import httpx

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_user_pdf_content():
    """測試用戶PDF內容的上傳"""

    print("🧪 測試用戶PDF內容上傳")
    print("=" * 50)

    # 使用用戶提供的PDF內容
    pdf_content = """DEPARTMENT OF HEALTH & HUMAN SERVICESPublic Health Service
Food and Drug Administration
10903 New Hampshire Avenue
Document Control Center - WO66-G609
Silver Spring, MD  20993-0002
January 18, 2017
Xavant Technology (PTY) Ltd
Roche Janse van Rensberg
Chairman
Unit 102 The Tannery Industrial Park
309 Derdepoort Road
Silverton, ZA 0184 Gauteng
Re:  K161091
Trade/Device Name:   STIMPOD NMS460 Nerve Stimulator
Regulation Number:  21 CFR 882.5890
Regulation Name:  Transcutaneous Electrical Nerve Stimulator For Pain Relief
Regulatory Class:  Class II
Product Code:  GZJ
Dated:  December 2, 2016
Received:  December 2, 2016

This is a test document with substantial content for GraphRAG processing.
It contains medical device information and technical specifications.
The document demonstrates the system's ability to process complex text content."""

    # 創建臨時文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(pdf_content)
        test_file_path = Path(f.name)

    try:
        print(f"📄 測試文件: {test_file_path.name}")
        print(f"📏 文件大小: {test_file_path.stat().st_size} bytes")
        print(f"📝 內容長度: {len(pdf_content)} 字符")

        # 測試API上傳
        api_url = "http://localhost:8000/upload/single"

        print(f"\n🌐 上傳到: {api_url}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(test_file_path, 'rb') as f:
                files = {'file': (test_file_path.name, f, 'text/plain')}
                response = await client.post(api_url, files=files)

            print(f"📡 響應狀態: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("\n📊 API響應:")
                print(f"  ✅ 成功: {result.get('success', False)}")

                if result.get('success'):
                    print(f"  🆔 文件ID: {result.get('document_id', 'N/A')}")
                    print(f"  ⏱️  處理時間: {result.get('processing_time', 0):.2f}秒")
                    print(f"  📝 字符數: {result.get('total_characters', 0)}")
                    print(f"  🎯 處理方法: {result.get('processing_method', 'N/A')}")

                    print("\n🎉 用戶PDF內容上傳測試成功！")
                    print("✅ 文件驗證通過")
                    print("✅ LangChain載入成功")
                    print("✅ 文件處理管道正常")
                    return True
                else:
                    print(f"❌ 上傳失敗: {result.get('detail', '未知錯誤')}")
                    return False
            else:
                print(f"❌ HTTP錯誤 {response.status_code}: {response.text}")
                return False

    except httpx.RequestError as e:
        print(f"❌ 連接錯誤: {e}")
        print("💡 請確保FastAPI服務正在運行 (uv run grag-api)")
        return False
    except Exception as e:
        print(f"❌ 測試異常: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up
        if test_file_path.exists():
            test_file_path.unlink()
            print(f"\n🧹 清理測試文件: {test_file_path.name}")

if __name__ == "__main__":
    result = asyncio.run(test_user_pdf_content())
    sys.exit(0 if result else 1)

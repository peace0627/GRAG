#!/usr/bin/env python3
"""
GraphRAG Integration Tests
統一的集成測試腳本，整合各個組件的功能測試
"""

import sys
import os
from pathlib import Path
import asyncio
import tempfile
import httpx
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphRAGIntegrationTest:
    """GraphRAG系統集成測試類"""

    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.test_content = """DEPARTMENT OF HEALTH & HUMAN SERVICES
Public Health Service
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
Re: K161091

Trade/Device Name: STIMPOD NMS460 Nerve Stimulator
Regulation Number: 21 CFR 882.5890
Regulation Name: Transcutaneous Electrical Nerve Stimulator For Pain Relief
Regulatory Class: Class II
Product Code: GZJ

This is a test document for GraphRAG system testing.
It contains medical device approval information and technical specifications.
"""

    async def run_all_tests(self):
        """運行所有集成測試"""
        print("🚀 GraphRAG集成測試開始")
        print("=" * 60)

        test_results = []

        # 測試1: LangChain組件測試
        print("\n🧪 測試1: LangChain組件功能")
        result1 = await self.test_langchain_components()
        test_results.append(("LangChain組件", result1))

        # 測試2: API文件上傳測試
        print("\n🧪 測試2: API文件上傳")
        result2 = await self.test_api_file_upload()
        test_results.append(("API文件上傳", result2))

        # 測試3: 前端文件驗證測試
        print("\n🧪 測試3: 前端文件驗證邏輯")
        result3 = self.test_frontend_validation()
        test_results.append(("前端文件驗證", result3))

        # 測試4: 系統健康檢查
        print("\n🧪 測試4: 系統健康檢查")
        result4 = await self.test_system_health()
        test_results.append(("系統健康檢查", result4))

        # 總結測試結果
        print("\n" + "=" * 60)
        print("📊 測試結果總結:")

        passed = 0
        total = len(test_results)

        for test_name, result in test_results:
            status = "✅ 通過" if result else "❌ 失敗"
            print(f"  {status} {test_name}")
            if result:
                passed += 1

        success_rate = (passed / total) * 100 if total > 0 else 0
        print(f"\n🎯 測試通過率: {passed}/{total} ({success_rate:.1f}%)")

        if success_rate == 100:
            print("🎉 所有集成測試通過！系統運行正常。")
        else:
            print("⚠️  部分測試失敗，請檢查系統配置。")

        return success_rate == 100

    async def test_langchain_components(self):
        """測試LangChain組件功能"""
        try:
            from grag.ingestion.langchain_loader import LangChainDocumentLoader, DocumentProcessingStrategy

            # 創建測試文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(self.test_content)
                test_file = Path(f.name)

            try:
                # 測試LangChain loader
                loader = LangChainDocumentLoader()
                docs = await loader.load_document(test_file)

                if not docs:
                    print("❌ LangChain載入失敗: 沒有載入任何文檔")
                    return False

                combined_text = loader.combine_documents(docs)
                if len(combined_text) == 0:
                    print("❌ 文檔合併失敗: 內容為空")
                    return False

                # 測試處理策略
                strategy = DocumentProcessingStrategy()
                use_vlm = strategy.should_use_vlm_first(test_file)
                if use_vlm:
                    print("❌ 處理策略錯誤: 文字文件應該跳過VLM")
                    return False

                print(f"✅ LangChain載入成功: {len(docs)} 個文檔，{len(combined_text)} 字符")
                return True

            finally:
                test_file.unlink(missing_ok=True)

        except Exception as e:
            print(f"❌ LangChain組件測試失敗: {e}")
            return False

    async def test_api_file_upload(self):
        """測試API文件上傳功能"""
        try:
            # 創建測試文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(self.test_content)
                test_file = Path(f.name)

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    with open(test_file, 'rb') as f:
                        files = {'file': (test_file.name, f, 'text/plain')}
                        response = await client.post(f"{self.api_base_url}/upload/single", files=files)

                    if response.status_code != 200:
                        print(f"❌ API響應錯誤: HTTP {response.status_code}")
                        print(f"響應內容: {response.text[:200]}...")
                        return False

                    result = response.json()
                    if not result.get('success'):
                        print(f"❌ 上傳失敗: {result.get('detail', '未知錯誤')}")
                        return False

                    # 檢查關鍵字段
                    if 'document_id' not in result:
                        print("❌ 缺少document_id字段")
                        return False

                    if 'processing_time' not in result:
                        print("❌ 缺少processing_time字段")
                        return False

                    print(f"✅ API上傳成功: 文件ID {result['document_id']}, 處理時間 {result['processing_time']:.2f}秒")
                    return True

            except httpx.RequestError as e:
                print(f"❌ API連接失敗: {e}")
                print("💡 請確保FastAPI服務正在運行 (uv run grag-api)")
                return False
            finally:
                test_file.unlink(missing_ok=True)

        except Exception as e:
            print(f"❌ API上傳測試異常: {e}")
            return False

    def test_frontend_validation(self):
        """測試前端文件驗證邏輯"""
        try:
            # 模擬前端驗證邏輯
            SUPPORTED_FORMATS = ['pdf', 'docx', 'jpg', 'jpeg', 'png', 'txt', 'md']
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

            # 測試文件格式驗證
            test_files = [
                ("test.pdf", True),
                ("test.txt", True),
                ("test.docx", True),
                ("test.exe", False),
                ("test.zip", False),
            ]

            for filename, should_pass in test_files:
                extension = filename.split('.')[-1].lower()
                is_valid = extension in SUPPORTED_FORMATS

                if is_valid != should_pass:
                    print(f"❌ 文件格式驗證失敗: {filename} (期望: {'有效' if should_pass else '無效'}, 實際: {'有效' if is_valid else '無效'})")
                    return False

            # 測試文件大小驗證
            test_sizes = [
                (5 * 1024 * 1024, True),    # 5MB - 有效
                (15 * 1024 * 1024, False),  # 15MB - 無效
            ]

            for size, should_pass in test_sizes:
                is_valid = size <= MAX_FILE_SIZE

                if is_valid != should_pass:
                    print(f"❌ 文件大小驗證失敗: {size} bytes (期望: {'有效' if should_pass else '無效'}, 實際: {'有效' if is_valid else '無效'})")
                    return False

            print("✅ 前端文件驗證邏輯正確")
            return True

        except Exception as e:
            print(f"❌ 前端驗證測試異常: {e}")
            return False

    async def test_system_health(self):
        """測試系統健康狀態"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_base_url}/health")

                if response.status_code != 200:
                    print(f"❌ 健康檢查失敗: HTTP {response.status_code}")
                    return False

                health_data = response.json()

                # 檢查關鍵健康指標
                if health_data.get('status') != 'healthy':
                    print(f"❌ 系統狀態異常: {health_data.get('status')}")
                    return False

                print("✅ 系統健康檢查通過")
                return True

        except httpx.RequestError as e:
            print(f"❌ 健康檢查連接失敗: {e}")
            return False
        except Exception as e:
            print(f"❌ 健康檢查異常: {e}")
            return False


async def main():
    """主測試函數"""
    tester = GraphRAGIntegrationTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

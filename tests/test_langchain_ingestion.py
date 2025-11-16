#!/usr/bin/env python3
"""Test script for LangChain-enhanced ingestion service"""

import sys
import os
from pathlib import Path
import unittest.mock as mock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import tempfile
import logging

from grag.ingestion.indexing.ingestion_service import IngestionService
from grag.ingestion.langchain_loader import LangChainDocumentLoader, DocumentProcessingStrategy, StructuredTextFallback
from grag.ingestion.indexing.chunking_service import ChunkingService
from grag.ingestion.indexing.embedding_service import EmbeddingService

# Set up logging
logging.basicConfig(level=logging.INFO)

async def test_langchain_components():
    """Test individual LangChain components without database dependencies"""

    print("🚀 測試LangChain元件")
    print("=" * 50)

    # Test 1: Document Loader
    print("🧪 測試1: LangChain文檔載入器")
    loader = LangChainDocumentLoader()

    test_content = """
# 測試文檔

這是一個測試Markdown文件。

## 章節

- 項目1
- 項目2

| 欄位 | 值 |
|------|----|
| 測試 | ✅ |
"""

    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_content)
        test_file_path = Path(f.name)

    try:
        langchain_docs = await loader.load_document(test_file_path)
        print(f"✅ 載入文檔成功: {len(langchain_docs)} 個chunks")

        combined_text = loader.combine_documents(langchain_docs)
        print(f"📏 合併後長度: {len(combined_text)} 字符")

        # Test 2: Processing Strategy
        print("\n🧪 測試2: 文件處理策略")
        strategy = DocumentProcessingStrategy()

        # Test different file types
        test_files = {
            test_file_path: False,  # .md should skip VLM (can process directly)
            test_file_path.with_suffix('.pdf'): True,  # .pdf should use VLM
            test_file_path.with_suffix('.txt'): False,  # .txt should skip VLM (can process directly)
        }

        for file_path, expect_vlm in test_files.items():
            use_vlm = strategy.should_use_vlm_first(file_path)
            print(f"📄 {file_path.suffix}: {'使用VLM' if use_vlm else '跳過VLM'} "
                  f"(預期: {'使用VLM' if expect_vlm else '跳過VLM'})")

        # Test override
        force_skip = strategy.should_use_vlm_first(test_file_path.with_suffix('.pdf'), use_vlm_override=False)
        force_use = strategy.should_use_vlm_first(test_file_path.with_suffix('.txt'), use_vlm_override=True)
        print(f"🔧 強制覆寫 - 跳過PDF VLM: {not force_skip}, 強制使用TXT VLM: {force_use}")

        # Test 3: Structured Fallback
        print("\n🧪 測試3: 結構化文字降級處理")
        fallback = StructuredTextFallback()

        # Mock LangChain documents
        from langchain_core.documents import Document as LangchainDocument
        mock_docs = [LangchainDocument(page_content=combined_text)]

        vlm_output = await fallback.create_structured_output(mock_docs, test_file_path, "test_file_id")
        print(f"✅ 結構化輸出 - 區域數: {len(vlm_output.regions)}, 表格數: {len(vlm_output.tables)}")
        print(f"📊 品質等級: {vlm_output.metadata.get('quality_level', 'unknown') if vlm_output.metadata else 'unknown'}")

        if vlm_output.regions:
            print("🎯 示例區域:")
            for i, region in enumerate(vlm_output.regions[:3]):
                print(f"  {i+1}. {region.modality}: {region.description[:50]}...")

        # Test 4: Chunking Service
        print("\n🧪 測試4: 分塊服務")
        chunker = ChunkingService()
        from uuid import UUID, uuid4
        test_uuid = uuid4()

        chunks = chunker.chunk_text(combined_text, test_uuid)
        print(f"✅ 分塊成功: {len(chunks)} 個chunks")
        if chunks:
            chunk_sizes = [chunk['metadata']['chunk_size'] for chunk in chunks]
            print(f"📏 Chunk大小統計: 最小{chunk_sizes[0]}, 最大{chunk_sizes[-1]}, 總字符: {sum(chunk_sizes)}")

        print(f"\n{'='*50}")
        print("🎉 LangChain元件測試完成!")

        return True

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up
        if test_file_path.exists():
            test_file_path.unlink()


async def main():
    """Main test runner"""
    success = await test_langchain_components()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
GraphRAG CLI Tool
命令行工具，用於測試和操作GraphRAG系統
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from grag.core.health_service import HealthService
from grag.core.database_services import DatabaseManager


class GraphRAGCLI:
    """GraphRAG命令行工具"""

    def __init__(self):
        self.health_service = HealthService()
        self.db_manager = None

    async def initialize_db(self):
        """初始化資料庫管理器"""
        if self.db_manager is None:
            from grag.core.config import settings
            self.db_manager = DatabaseManager(
                neo4j_uri=settings.neo4j_uri,
                neo4j_user=settings.neo4j_user,
                neo4j_password=settings.neo4j_password,
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_key
            )
            await self.db_manager.initialize()

    async def health(self, args):
        """檢查系統健康狀態"""
        print("=== 系統健康檢查 ===")

        try:
            status = self.health_service.get_system_status()

            print(f"時間戳: {status['timestamp']}")
            print(f"整體健康度: {status['overall_health']}")
            print()

            print("服務狀態:")
            services = status.get('database', {})
            print(f"  Neo4j:    {'✅' if services.get('neo4j') else '❌'}")
            print(f"  Supabase: {'✅' if services.get('supabase') else '❌'}")
            print(f"  LangChain:{'✅' if status.get('langchain') else '❌'}")
            print(f"  VLM:      {'✅' if status.get('vlm_configured') else '❌'}")
            print(f"  嵌入服務:  {'✅' if status.get('embedding_service') else '❌'}")

        except Exception as e:
            print(f"錯誤: {str(e)}")
            return 1

        return 0

    async def upload(self, args):
        """上傳和處理文件"""
        if not args.file:
            print("錯誤: 請提供文件路徑")
            return 1

        file_path = Path(args.file)
        if not file_path.exists():
            print(f"錯誤: 文件不存在 - {file_path}")
            return 1

        print(f"=== 上傳文件: {file_path.name} ===")

        try:
            # 初始化上傳服務
            from grag.ingestion.indexing.ingestion_service import IngestionService
            ingestion_service = IngestionService()

            # 處理文件
            result = await ingestion_service.ingest_document_enhanced(
                file_path=file_path,
                force_vlm=args.force_vlm
            )

            if result.get("success"):
                print("✅ 文件處理成功！")
                metadata = result.get("metadata", {})
                print(f"  創建的chunks: {metadata.get('chunks_created', 0)}")
                print(f"  創建的embeddings: {metadata.get('embeddings_created', 0)}")
                return 0
            else:
                print(f"❌ 處理失敗: {result.get('error', '未知錯誤')}")
                return 1

        except Exception as e:
            print(f"錯誤: {str(e)}")
            return 1

    async def delete(self, args):
        """删除文檔"""
        if not args.document_id:
            print("錯誤: 請提供文檔ID")
            return 1

        try:
            from uuid import UUID
            doc_uuid = UUID(args.document_id)

            print(f"=== 删除文檔: {args.document_id} ===")

            await self.initialize_db()
            result = await self.db_manager.delete_document_cascade(doc_uuid)

            if result:
                print("✅ 文檔删除成功！")
                print("  已清理Neo4j圖形數據和Supabase向量數據")
                return 0
            else:
                print("❌ 删除失敗")
                return 1

        except ValueError:
            print(f"錯誤: 無效的文檔ID格式 - {args.document_id}")
            return 1
        except Exception as e:
            print(f"錯誤: {str(e)}")
            return 1

    async def stats(self, args):
        """顯示資料庫統計"""
        print("=== 資料庫統計 ===")
        print("統計功能即將實現，目前使用Neo4j Browser查看詳細統計")
        print("提示: 打開 http://localhost:7474 以查看Neo4j數據庫")
        return 0

    async def close(self):
        """清理資源"""
        if self.db_manager:
            await self.db_manager.close()


async def main():
    """主函數"""
    cli = GraphRAGCLI()

    try:
        # 設置參數解析器
        parser = argparse.ArgumentParser(
            description="GraphRAG CLI Tool",
            prog="grag"
        )

        subparsers = parser.add_subparsers(dest='command', help='可用命令')

        # health 命令
        health_parser = subparsers.add_parser('health', help='檢查系統健康狀態')
        health_parser.set_defaults(func=cli.health)

        # upload 命令
        upload_parser = subparsers.add_parser('upload', help='上傳並處理文件')
        upload_parser.add_argument('file', help='要處理的文件路徑')
        upload_parser.add_argument('--force-vlm', action='store_true', help='強制使用VLM處理')
        upload_parser.set_defaults(func=cli.upload)

        # delete 命令
        delete_parser = subparsers.add_parser('delete', help='删除文檔')
        delete_parser.add_argument('document_id', help='要删除的文檔ID')
        delete_parser.set_defaults(func=cli.delete)

        # stats 命令
        stats_parser = subparsers.add_parser('stats', help='顯示資料庫統計')
        stats_parser.set_defaults(func=cli.stats)

        # 解析參數
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return 1

        # 執行對應的命令
        result = args.func(args)
        if asyncio.iscoroutine(result):
            return await result
        else:
            return result

    except KeyboardInterrupt:
        print("\n用戶中斷")
        return 1
    except Exception as e:
        print(f"未預期的錯誤: {str(e)}")
        return 1
    finally:
        await cli.close()


def sync_main():
    """同步入口點，主要用於非異步環境"""
    return asyncio.run(main())


if __name__ == "__main__":
    exit_code = sync_main()
    sys.exit(exit_code)

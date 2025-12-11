#!/usr/bin/env python3
"""
Agent測試腳本
用於測試Agentic RAG的功能
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from grag.agents.rag_agent import AgenticRAGAgent
from grag.agents.planner import QueryPlanner


class AgentTester:
    """Agent測試工具類"""

    def __init__(self):
        self.agent = None

    async def initialize(self):
        """初始化Agent"""
        print("🔧 初始化Agentic RAG Agent...")
        try:
            self.agent = AgenticRAGAgent()
            print("✅ Agent初始化成功")

            # 測試系統狀態
            status = await self.agent.get_system_status()
            print(f"📊 系統狀態: {status.get('status', 'unknown')}")
            print(f"🤖 可用Agent: {len(status.get('agents', {}))}")
            print(f"🛠️ 可用工具: {status.get('tools_available', 0)}")

            return True
        except Exception as e:
            print(f"❌ Agent初始化失敗: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def test_planner_only(self, query: str) -> Dict[str, Any]:
        """只測試查詢規劃器"""
        print(f"\n🗂️ 測試查詢規劃器: {query}")
        print("-" * 40)

        try:
            planner = QueryPlanner()
            planner_output = await planner.plan_query(query)

            print("✅ 規劃器執行成功")
            print(f"   查詢類型: {planner_output.query_type}")
            print(f"   複雜度: {planner_output.estimated_complexity:.2f}")
            print(f"   執行步驟: {len(planner_output.execution_plan)}")
            print(f"   建議工具: {[t.value for t in planner_output.suggested_tools]}")

            # 打印執行計劃
            print("   執行計劃:")
            for i, step in enumerate(planner_output.execution_plan, 1):
                print(f"     {i}. {step.description} ({step.tool_type.value})")

            return {
                "query_type": planner_output.query_type.value,
                "complexity": planner_output.estimated_complexity,
                "steps": len(planner_output.execution_plan),
                "tools": [t.value for t in planner_output.suggested_tools]
            }

        except Exception as e:
            error_msg = f"❌ 規劃器測試失敗: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return {"error": error_msg}

    async def test_basic_query(self, query: str) -> Dict[str, Any]:
        """測試基本查詢功能"""
        if not self.agent:
            return {"error": "Agent未初始化"}

        print(f"\n🤖 測試查詢: {query}")
        print("-" * 50)

        try:
            result = await self.agent.query(query)

            # 打印結果摘要
            print("✅ 查詢成功")
            print(f"   查詢ID: {result.get('query_id', 'unknown')}")
            print(f"   查詢類型: {result.get('query_type', 'unknown')}")
            print(f"   信心分數: {result.get('confidence_score', 0):.2f}")
            print(f"   證據數量: {result.get('evidence_count', 0)}")
            print(f"   執行時間: {result.get('execution_time', 0):.2f}")
            print(f"   需要澄清: {result.get('needs_clarification', False)}")

            # 打印最終答案
            answer = result.get('final_answer', '')
            print(f"\n📝 最終答案:\n{answer}")

            # 打印證據摘要
            evidence = result.get('evidence', [])
            if evidence:
                print(f"\n🔍 證據摘要 (前{len(evidence)}條):")
                for i, ev in enumerate(evidence[:3], 1):
                    print(f"   {i}. [{ev.get('source_type', 'unknown')}] {ev.get('content', '')[:100]}...")

            return result

        except Exception as e:
            error_msg = f"❌ 查詢失敗: {str(e)}"
            print(error_msg)
            return {"error": error_msg}

    async def test_multiple_queries(self, queries: List[str]):
        """測試多個查詢"""
        print(f"🧪 將測試 {len(queries)} 個查詢")

        results = []
        for i, query in enumerate(queries, 1):
            print(f"\n{'='*60}")
            print(f"測試 {i}/{len(queries)}")
            result = await self.test_basic_query(query)
            results.append(result)

        # 總結結果
        self._print_summary(results)

        return results

    def _print_summary(self, results: List[Dict[str, Any]]):
        """打印測試總結"""
        print(f"\n{'='*60}")
        print("📊 測試總結")
        print(f"{'='*60}")

        total = len(results)
        successful = sum(1 for r in results if 'error' not in r)
        failed = total - successful

        print(f"總查詢數: {total}")
        print(f"成功: {successful}")
        print(f"失敗: {failed}")

        if successful > 0:
            avg_confidence = sum(r.get('confidence_score', 0) for r in results if 'error' not in r) / successful
            avg_time = sum(r.get('execution_time', 0) for r in results if 'error' not in r) / successful

            print(f"   平均信心分數: {avg_confidence:.2f}")
            print(f"   平均執行時間: {avg_time:.2f}秒")
        if failed > 0:
            print("失敗的查詢:")
            for i, result in enumerate(results, 1):
                if 'error' in result:
                    print(f"  {i}. {result['error']}")


async def interactive_test():
    """互動式測試"""
    tester = AgentTester()

    if not await tester.initialize():
        return

    print("\n🎮 進入互動測試模式")
    print("輸入 'quit' 退出, 'test' 運行預設測試")
    print("-" * 50)

    # 預設測試查詢
    default_queries = [
        "請介紹一下這個系統的主要功能",
        "系統支持哪些數據庫？",
        "如何處理多模態數據？",
        "What are the main components of this GraphRAG system?"
    ]

    while True:
        try:
            user_input = input("\n🔍 輸入查詢 (或 'quit' 退出, 'test' 預設測試): ").strip()

            if user_input.lower() == 'quit':
                print("👋 再見！")
                break
            elif user_input.lower() == 'test':
                await tester.test_multiple_queries(default_queries)
            elif user_input:
                await tester.test_basic_query(user_input)
            else:
                print("請輸入有效的查詢")

        except KeyboardInterrupt:
            print("\n👋 用戶中斷，再見！")
            break
        except Exception as e:
            print(f"❌ 測試錯誤: {str(e)}")


async def main():
    """主函數"""
    if len(sys.argv) > 1:
        # 命令行模式
        query = " ".join(sys.argv[1:])
        tester = AgentTester()

        if await tester.initialize():
            await tester.test_basic_query(query)
    else:
        # 互動模式
        await interactive_test()


if __name__ == "__main__":
    print("🚀 GraphRAG Agent測試工具")
    print("=" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 測試中斷")
    except Exception as e:
        print(f"❌ 測試工具錯誤: {str(e)}")
        sys.exit(1)

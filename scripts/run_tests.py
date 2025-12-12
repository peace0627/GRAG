#!/usr/bin/env python3
"""
GraphRAG 測試運行器
統一的測試入口腳本
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_integration_tests():
    """運行集成測試"""
    print("🚀 運行GraphRAG集成測試...")
    from tests.integration_test import main as integration_main
    return asyncio.run(integration_main())

def run_unit_tests():
    """運行單元測試"""
    print("🧪 運行GraphRAG單元測試...")
    import subprocess
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], cwd=project_root)
    return result.returncode == 0

def run_specific_test(test_file):
    """運行特定測試文件"""
    test_path = Path("tests") / test_file
    if not test_path.exists():
        test_path = Path(test_file)
        if not test_path.exists():
            print(f"❌ 測試文件不存在: {test_file}")
            return False

    print(f"🎯 運行測試文件: {test_path}")
    import subprocess
    result = subprocess.run([sys.executable, str(test_path)], cwd=project_root)
    return result.returncode == 0

def list_tests():
    """列出所有可用的測試"""
    print("📋 可用的測試文件:")
    print("\n集成測試:")
    print("  integration_test.py     - 系統集成測試 (推薦)")

    print("\n單元測試:")
    tests_dir = Path("tests")
    if tests_dir.exists():
        for test_file in sorted(tests_dir.glob("test_*.py")):
            if test_file.name != "integration_test.py":
                print(f"  {test_file.name}")

    print("\n開發測試 (根目錄):")
    for test_file in sorted(project_root.glob("test_*.py")):
        print(f"  {test_file.name}")

    print("\n運行方式:")
    print("  python scripts/run_tests.py integration    # 運行集成測試")
    print("  python scripts/run_tests.py unit          # 運行所有單元測試")
    print("  python scripts/run_tests.py test_file.py  # 運行特定測試")
    print("  python scripts/run_tests.py list          # 列出所有測試")

def main():
    parser = argparse.ArgumentParser(description="GraphRAG 測試運行器")
    parser.add_argument("command", choices=["integration", "unit", "list"], help="測試命令")
    parser.add_argument("test_file", nargs="?", help="特定的測試文件")

    args = parser.parse_args()

    if args.command == "list":
        list_tests()
        return True

    elif args.command == "integration":
        success = run_integration_tests()

    elif args.command == "unit":
        success = run_unit_tests()

    else:
        if args.test_file:
            success = run_specific_test(args.test_file)
        else:
            print("❌ 請指定測試文件")
            return False

    if success:
        print("\n🎉 測試完成!")
        sys.exit(0)
    else:
        print("\n❌ 測試失敗!")
        sys.exit(1)

if __name__ == "__main__":
    main()

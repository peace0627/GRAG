#!/usr/bin/env python3
"""
測試多主機 Ollama 客戶端功能
"""

from ollama_client import (
    MultiHostOllamaClient,
    SimpleOllamaClient,
    LoadBalancingStrategy,
    get_ollama_client
)


def test_multi_host_client():
    """測試多主機客戶端基本功能"""
    print("🧪 測試多主機 Ollama 客戶端...")

    # 創建多主機客戶端
    client = MultiHostOllamaClient(
        hosts=["http://localhost:11434"],
        model="gemma3:4b",
        load_balancing=LoadBalancingStrategy.ROUND_ROBIN,
        failover=True
    )

    print(f"  📋 配置的主機: {[host.url for host in client.hosts]}")
    print(f"  ⚙️ 負載均衡策略: {client.load_balancing}")
    print(f"  🔄 故障轉移: {client.failover}")

    # 測試主機狀態
    status = client.get_host_status()
    print(f"  📊 主機狀態: {len(status)} 個主機")
    for host_info in status:
        print(f"    • {host_info['url']}: {host_info['status']}")

    print("✅ 多主機客戶端初始化測試通過")


def test_simple_client():
    """測試簡單客戶端（向下相容）"""
    print("🧪 測試簡單 Ollama 客戶端...")

    # 測試預設客戶端
    client = SimpleOllamaClient()
    print("  📱 創建預設簡單客戶端")

    # 測試指定主機的客戶端
    client_with_host = SimpleOllamaClient(host="http://localhost:11434", model="gemma3:4b")
    print("  🖥️ 創建指定主機的簡單客戶端")

    print("✅ 簡單客戶端測試通過")


def test_environment_variables():
    """測試環境變數配置"""
    print("🧪 測試環境變數配置...")

    # 測試全域客戶端（使用環境變數）
    global_client = get_ollama_client()
    print(f"  🌍 全域客戶端配置: {len(global_client.hosts)} 個主機")
    print(f"  🤖 預設模型: {global_client.model}")
    print(f"  ⏱️ 超時設定: {global_client.timeout}秒")

    print("✅ 環境變數配置測試通過")


def test_host_management():
    """測試主機管理功能"""
    print("🧪 測試主機管理功能...")

    client = MultiHostOllamaClient(hosts=["http://localhost:11434"])

    initial_count = len(client.hosts)
    print(f"  📊 初始主機數量: {initial_count}")

    # 添加主機
    client.add_host("http://gpu-server:11434")
    print(f"  ➕ 添加主機後: {len(client.hosts)} 個主機")

    # 重複添加（應該不會重複）
    client.add_host("http://localhost:11434")
    print(f"  🔄 重複添加後: {len(client.hosts)} 個主機")

    # 移除主機
    client.remove_host("http://gpu-server:11434")
    print(f"  ➖ 移除主機後: {len(client.hosts)} 個主機")

    assert len(client.hosts) == initial_count, "主機管理功能異常"
    print("✅ 主機管理測試通過")


def test_load_balancing_strategies():
    """測試負載均衡策略"""
    print("🧪 測試負載均衡策略...")

    # 測試 Round Robin
    rr_client = MultiHostOllamaClient(
        hosts=["http://host1:11434", "http://host2:11434", "http://host3:11434"],
        load_balancing=LoadBalancingStrategy.ROUND_ROBIN
    )
    print(f"  🔄 Round Robin 策略: {rr_client.load_balancing}")

    # 測試 Random
    random_client = MultiHostOllamaClient(
        hosts=["http://host1:11434", "http://host2:11434"],
        load_balancing=LoadBalancingStrategy.RANDOM
    )
    print(f"  🎲 Random 策略: {random_client.load_balancing}")

    # 測試 Priority
    priority_client = MultiHostOllamaClient(
        hosts=["http://host1:11434", "http://host2:11434"],
        load_balancing=LoadBalancingStrategy.PRIORITY
    )
    print(f"  ⭐ Priority 策略: {priority_client.load_balancing}")

    print("✅ 負載均衡策略測試通過")


if __name__ == "__main__":
    print("🚀 開始 Ollama 多主機客戶端測試\n")

    try:
        test_multi_host_client()
        print()
        test_simple_client()
        print()
        test_environment_variables()
        print()
        test_host_management()
        print()
        test_load_balancing_strategies()
        print()
        print("🎉 所有 Ollama 客戶端測試通過！")
    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        raise

"""
Ollama 多主機客戶端 - 支援負載均衡和故障轉移

提供智慧的 Ollama 連線管理，支援多個主機、自動故障轉移、
健康檢查和負載均衡功能。
"""

import asyncio
import time
import random
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum

import ollama
from dotenv import load_dotenv
import os

# 加載環境變數
load_dotenv()


class LoadBalancingStrategy(str, Enum):
    """負載均衡策略"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    PRIORITY = "priority"  # 優先使用第一個可用的主機


class HostStatus(str, Enum):
    """主機狀態"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class OllamaHost:
    """Ollama 主機信息"""
    url: str
    status: HostStatus = HostStatus.UNKNOWN
    last_check: float = 0.0
    response_time: float = 0.0
    consecutive_failures: int = 0


class MultiHostOllamaClient:
    """
    多主機 Ollama 客戶端

    支援：
    - 多個 Ollama 服務器
    - 負載均衡 (round-robin, random, priority)
    - 自動故障轉移
    - 健康檢查
    - 重試機制
    """

    def __init__(
        self,
        hosts: List[str] = None,
        model: str = None,
        timeout: int = 300,
        load_balancing: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        failover: bool = True,
        health_check_interval: int = 30,
        max_retries: int = 3
    ):
        # 從環境變數讀取配置
        if hosts is None:
            hosts_str = os.getenv('OLLAMA_HOSTS', 'http://localhost:11434')
            hosts = [host.strip() for host in hosts_str.split(',') if host.strip()]

        self.model = model or os.getenv('OLLAMA_MODEL', 'gemma3:4b')
        self.timeout = timeout or int(os.getenv('OLLAMA_TIMEOUT', '300'))
        self.load_balancing = LoadBalancingStrategy(
            load_balancing or os.getenv('OLLAMA_LOAD_BALANCING', 'round_robin')
        )
        self.failover = failover or os.getenv('OLLAMA_FAILOVER', 'true').lower() == 'true'
        self.health_check_interval = health_check_interval or int(os.getenv('OLLAMA_HEALTH_CHECK_INTERVAL', '30'))
        self.max_retries = max_retries or int(os.getenv('OLLAMA_MAX_RETRIES', '3'))

        # 初始化主機
        self.hosts = [OllamaHost(url=url) for url in hosts]
        self.current_host_index = 0
        self.last_health_check = 0

        # 啟動健康檢查任務
        self._start_health_check()

    def _start_health_check(self):
        """啟動背景健康檢查"""
        # 在生產環境中，這應該是一個獨立的任務
        # 這裡簡化為同步檢查
        pass

    async def _check_host_health(self, host: OllamaHost) -> bool:
        """檢查主機健康狀態"""
        try:
            start_time = time.time()
            client = ollama.Client(host=host.url, timeout=10)

            # 簡單的健康檢查：列出模型
            models = client.list()
            response_time = time.time() - start_time

            host.status = HostStatus.HEALTHY
            host.response_time = response_time
            host.last_check = time.time()
            host.consecutive_failures = 0

            return True

        except Exception as e:
            host.status = HostStatus.UNHEALTHY
            host.last_check = time.time()
            host.consecutive_failures += 1
            return False

    def _get_next_host(self) -> Optional[OllamaHost]:
        """根據負載均衡策略選擇下一個主機"""
        healthy_hosts = [host for host in self.hosts if host.status == HostStatus.HEALTHY]

        if not healthy_hosts:
            # 如果沒有健康的主機，嘗試檢查所有主機
            self._perform_health_check()
            healthy_hosts = [host for host in self.hosts if host.status == HostStatus.HEALTHY]

        if not healthy_hosts:
            return None

        if self.load_balancing == LoadBalancingStrategy.ROUND_ROBIN:
            host = healthy_hosts[self.current_host_index % len(healthy_hosts)]
            self.current_host_index += 1
            return host

        elif self.load_balancing == LoadBalancingStrategy.RANDOM:
            return random.choice(healthy_hosts)

        elif self.load_balancing == LoadBalancingStrategy.PRIORITY:
            # 返回響應時間最快的主機
            return min(healthy_hosts, key=lambda h: h.response_time)

        return healthy_hosts[0]

    def _perform_health_check(self):
        """執行健康檢查"""
        current_time = time.time()
        if current_time - self.last_health_check < self.health_check_interval:
            return

        self.last_health_check = current_time

        for host in self.hosts:
            asyncio.run(self._check_host_health(host))

    def _create_client_for_host(self, host: OllamaHost) -> ollama.Client:
        """為指定主機創建 Ollama 客戶端"""
        return ollama.Client(host=host.url, timeout=self.timeout)

    def generate(
        self,
        prompt: str,
        model: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成回應，支援自動故障轉移

        Args:
            prompt: 輸入提示
            model: 模型名稱（可選）
            **kwargs: 其他參數

        Returns:
            生成的回應

        Raises:
            Exception: 當所有主機都不可用時
        """
        model = model or self.model
        last_exception = None

        for attempt in range(self.max_retries):
            host = self._get_next_host()

            if host is None:
                raise Exception("所有 Ollama 主機都不可用")

            try:
                client = self._create_client_for_host(host)
                response = client.generate(
                    model=model,
                    prompt=prompt,
                    **kwargs
                )
                return response

            except Exception as e:
                last_exception = e
                host.status = HostStatus.UNHEALTHY
                host.consecutive_failures += 1

                if self.failover and attempt < self.max_retries - 1:
                    continue
                else:
                    break

        raise last_exception or Exception("生成失敗")

    def list_models(self) -> Dict[str, Any]:
        """列出可用模型"""
        host = self._get_next_host()
        if host is None:
            raise Exception("所有 Ollama 主機都不可用")

        client = self._create_client_for_host(host)
        return client.list()

    def get_host_status(self) -> List[Dict[str, Any]]:
        """獲取所有主機狀態"""
        self._perform_health_check()
        return [
            {
                "url": host.url,
                "status": host.status,
                "response_time": host.response_time,
                "last_check": host.last_check,
                "consecutive_failures": host.consecutive_failures
            }
            for host in self.hosts
        ]

    def add_host(self, url: str):
        """添加新主機"""
        if not any(host.url == url for host in self.hosts):
            self.hosts.append(OllamaHost(url=url))

    def remove_host(self, url: str):
        """移除主機"""
        self.hosts = [host for host in self.hosts if host.url != url]


# 全域單例實例
_ollama_client = None


def get_ollama_client() -> MultiHostOllamaClient:
    """獲取全域 Ollama 客戶端實例"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = MultiHostOllamaClient()
    return _ollama_client


def create_ollama_client(
    hosts: List[str] = None,
    model: str = None,
    **kwargs
) -> MultiHostOllamaClient:
    """創建新的 Ollama 客戶端實例"""
    return MultiHostOllamaClient(hosts=hosts, model=model, **kwargs)


# 向下相容的簡單介面
class SimpleOllamaClient:
    """簡單的 Ollama 客戶端，保持與原有代碼相容"""

    def __init__(self, host: str = None, model: str = None):
        self.client = get_ollama_client()
        if host:
            # 如果指定了特定主機，創建臨時客戶端
            self.temp_client = MultiHostOllamaClient(hosts=[host], model=model)

    def generate(self, prompt: str, model: str = None, **kwargs):
        if hasattr(self, 'temp_client'):
            return self.temp_client.generate(prompt, model, **kwargs)
        return self.client.generate(prompt, model, **kwargs)

    def list(self):
        return self.client.list_models()

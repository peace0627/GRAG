"""
Cache Manager
獨立的快取管理器，提供LRU快取實現，不依賴任何前端框架
支持TTL、鍵前綴管理和自動清理
"""

import asyncio
from typing import Dict, Any, Optional, Callable
import time
import hashlib
import threading
from functools import wraps
import json


class CacheEntry:
    """快取條目"""

    def __init__(self, data: Any, ttl_seconds: int):
        self.data = data
        self.expiration_time = time.time() + ttl_seconds
        self.created_time = time.time()

    def is_expired(self) -> bool:
        """檢查是否過期"""
        return time.time() > self.expiration_time

    def remaining_ttl(self) -> float:
        """返回剩餘TTL（秒）"""
        return max(0, self.expiration_time - time.time())


class CacheManager:
    """獨立快取管理器"""

    def __init__(self, max_size: int = 1000, enable_cleanup: bool = True, cleanup_interval: int = 300):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = threading.RLock()

        # 清理任務
        if enable_cleanup:
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                daemon=True,
                args=(cleanup_interval,)
            )
            self._cleanup_thread.start()

    def cached_data(self, ttl_seconds: int = 300, key_prefix: str = ""):
        """
        數據快取裝飾器

        Args:
            ttl_seconds: 快取到期時間(秒)
            key_prefix: 快取鍵前綴，用於區分不同函數
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成快取鍵
                cache_key = self._generate_cache_key(func.__name__, args, kwargs, key_prefix)

                # 嘗試從快取獲取
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # 執行函數並快取結果
                try:
                    result = func(*args, **kwargs)
                    self.set(cache_key, result, ttl_seconds)
                    return result
                except Exception as e:
                    # 記錄錯誤但不中斷
                    self._log_cache_error(f"快取函數 {func.__name__} 執行失敗", e)
                    return {'success': False, 'error': str(e)}

            return wrapper
        return decorator

    def get(self, key: str) -> Any:
        """從快取獲取數據"""
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                return entry.data
            elif entry and entry.is_expired():
                # 刪除過期的條目
                del self._cache[key]
            return None

    def set(self, key: str, data: Any, ttl_seconds: int) -> bool:
        """設置快取數據"""
        with self._lock:
            # 檢查容量限制
            if len(self._cache) >= self._max_size:
                self._evict_oldest()

            self._cache[key] = CacheEntry(data, ttl_seconds)
            return True

    def delete(self, key: str) -> bool:
        """刪除快取條目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear_by_prefix(self, prefix: str) -> int:
        """根據前綴清除快取條目"""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def clear_expired(self) -> int:
        """清除過期的快取條目"""
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """獲取快取統計信息"""
        with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for v in self._cache.values() if v.is_expired())

            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'active_entries': total_entries - expired_entries,
                'max_size': self._max_size,
                'cache_hit_rate': 0.0  # 需要額外追蹤
            }

    def _generate_cache_key(self, func_name: str, args, kwargs, prefix: str) -> str:
        """生成快取鍵"""
        # 將參數序列化為字符串
        try:
            args_str = json.dumps(args, sort_keys=True, default=str)
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
            content = f"{prefix}_{func_name}_{args_str}_{kwargs_str}"
        except (TypeError, ValueError):
            # 如果無法序列化，使用字串表示
            args_str = str(args) + str(sorted(kwargs.items()))
            content = f"{prefix}_{func_name}_{args_str}"

        # 生成MD5哈希
        return hashlib.md5(content.encode()).hexdigest()

    def _evict_oldest(self):
        """清除最舊的快取條目 (LRU策略簡化版)"""
        if not self._cache:
            return

        # 簡單實現：刪除創建時間最早的10個條目
        entries_to_remove = sorted(
            self._cache.items(),
            key=lambda x: x[1].created_time
        )[:10]

        for key, _ in entries_to_remove:
            del self._cache[key]

    def _cleanup_worker(self, interval: int):
        """定期清理工作"""
        while True:
            time.sleep(interval)
            try:
                cleared = self.clear_expired()
                if cleared > 0:
                    print(f"[CacheManager] Cleaned {cleared} expired entries")
            except Exception as e:
                print(f"[CacheManager] Cleanup error: {e}")

    def _log_cache_error(self, message: str, error: Exception):
        """記錄快取錯誤"""
        error_msg = f"[快取錯誤] {message}: {str(error)}"
        print(error_msg[:200] + "..." if len(error_msg) > 200 else error_msg)

    def create_error_safe_wrapper(self, func: Callable, fallback_value: Any = None):
        """
        創建錯誤安全的包裝函數

        Args:
            func: 要包裝的函數
            fallback_value: 函數失敗時的返回值
        """
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self._log_cache_error(f"函數 {func.__name__} 執行失敗", e)
                return fallback_value
        return wrapper


# 全域快取管理器實例
cache_manager = CacheManager()

# 便捷裝飾器
def cached_data(ttl_seconds: int = 300, key_prefix: str = ""):
    """便捷的數據快取裝飾器"""
    return cache_manager.cached_data(ttl_seconds, key_prefix)

def error_safe(fallback_value: Any = None):
    """錯誤安全裝飾器"""
    def decorator(func):
        return cache_manager.create_error_safe_wrapper(func, fallback_value)
    return decorator

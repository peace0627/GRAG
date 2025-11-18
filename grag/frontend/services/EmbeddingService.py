"""
Embedding Service
嵌入服務管理，提供嵌入提供者的統一介面
"""
from typing import Dict, List, Any, Optional

class EmbeddingService:
    """嵌入服務管理"""

    def __init__(self):
        self._providers_cache = None
        self._provider_info_cache = {}

    def get_available_providers(self) -> List[str]:
        """獲取所有可用的嵌入提供者"""
        if self._providers_cache is None:
            try:
                from grag.ingestion.indexing.providers.embedding_providers import list_available_providers
                self._providers_cache = list_available_providers()
            except Exception:
                # 如果載入失敗，返回基本提供者列表
                self._providers_cache = ['sentence_transformers']

        return self._providers_cache

    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """獲取指定提供者的資訊"""
        if provider_name not in self._provider_info_cache:
            try:
                from grag.ingestion.indexing.providers.embedding_providers import get_provider_info
                info = get_provider_info(provider_name)
                if info:
                    self._provider_info_cache[provider_name] = info
                else:
                    # 提供預設資訊
                    self._provider_info_cache[provider_name] = self._get_default_provider_info(provider_name)
            except Exception:
                # 如果載入失敗，提供預設資訊
                self._provider_info_cache[provider_name] = self._get_default_provider_info(provider_name)

        return self._provider_info_cache.get(provider_name)

    def check_provider_status(self, provider_name: str) -> Dict[str, Any]:
        """檢查提供者的可用狀態"""
        try:
            from grag.ingestion.indexing.providers.embedding_providers import create_embedding_provider

            provider = create_embedding_provider(provider_name)
            available = provider.is_available()
            name = getattr(provider, 'name', provider_name)

            if available:
                return {
                    'available': True,
                    'name': name,
                    'error': None,
                    'dimension': getattr(provider, 'dimension', None)
                }
            else:
                return {
                    'available': False,
                    'name': name,
                    'error': '提供者無法初始化',
                    'dimension': None
                }

        except Exception as e:
            return {
                'available': False,
                'name': provider_name,
                'error': str(e),
                'dimension': None
            }

    def _get_default_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """獲取預設提供者資訊"""
        defaults = {
            'sentence_transformers': {
                'dimension': 384,
                'cost': 'Free',
                'description': '高品質本地嵌入模型，適合大多數應用場景'
            },
            'openai': {
                'dimension': 1536,
                'cost': 'Pay per use',
                'description': 'OpenAI的text-embedding-ada-002模型，雲端服務'
            },
            'cohere': {
                'dimension': 4096,
                'cost': 'Pay per use',
                'description': 'Cohere的嵌入模型，企業級服務'
            },
            'clip': {
                'dimension': 512,
                'cost': 'Free',
                'description': '多模態嵌入模型，支援文字和圖片'
            }
        }

        return defaults.get(provider_name, {
            'dimension': 'Unknown',
            'cost': 'Unknown',
            'description': '嵌入提供者資訊不可用'
        })

    def validate_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """驗證提供者配置是否完整"""
        result = {
            'valid': False,
            'missing_config': [],
            'warnings': []
        }

        # 檢查不同提供者的特定配置需求
        if provider_name == 'openai':
            from grag.core.config import settings
            if not getattr(settings, 'openai_api_key', None):
                result['missing_config'].append('OPENAI_API_KEY')

        elif provider_name == 'cohere':
            from grag.core.config import settings
            if not getattr(settings, 'cohere_api_key', None):
                result['missing_config'].append('COHERE_API_KEY')

        # 如果沒有缺失配置，標記為有效
        if not result['missing_config']:
            result['valid'] = True

        return result

    def get_recommended_provider(self, use_case: str = 'general') -> str:
        """根據使用場景推薦提供者"""
        recommendations = {
            'general': 'sentence_transformers',
            'multimodal': 'clip',
            'enterprise': 'cohere',
            'local_only': 'sentence_transformers',
            'high_performance': 'openai'
        }

        return recommendations.get(use_case, 'sentence_transformers')

    def compare_providers(self) -> Dict[str, Dict[str, Any]]:
        """比較所有可用提供者的特性"""
        providers = self.get_available_providers()
        comparison = {}

        for provider in providers:
            info = self.get_provider_info(provider)
            status = self.check_provider_status(provider)
            config_valid = self.validate_provider_config(provider)

            comparison[provider] = {
                'info': info,
                'status': status,
                'config_valid': config_valid,
                'ready_to_use': status['available'] and config_valid['valid']
            }

        return comparison

    def clear_cache(self):
        """清除快取"""
        self._providers_cache = None
        self._provider_info_cache.clear()

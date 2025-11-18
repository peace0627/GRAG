"""
System Check Service
系統狀態檢查服務，提供各項系統組件的可用性檢查
"""
import streamlit as st
from typing import Dict, Any, Optional
from grag.core.config import settings

class SystemCheckService:
    """系統狀態檢查服務"""

    def __init__(self):
        pass

    def get_system_status(self) -> Dict[str, Any]:
        """
        獲取完整的系統狀態

        Returns:
            dict: 包含各項服務狀態的字典
        """
        status = {
            'timestamp': self._get_timestamp(),
            'overall_health': 'unknown'
        }

        # 檢查各項服務
        status.update({
            'langchain': self._check_langchain(),
            'vlm_configured': self._check_vlm_config(),
            'database': self._check_database_connections(),
            'embedding_service': self._check_embedding_service()
        })

        # 總體健康評估
        status['overall_health'] = self._assess_overall_health(status)

        return status

    def _check_langchain(self) -> bool:
        """檢查 LangChain 安裝狀態"""
        try:
            import langchain_community
            return True
        except ImportError:
            return False

    def _check_vlm_config(self) -> bool:
        """檢查 VLM 配置狀態"""
        vlm_sources = []

        # 檢查 Ollama
        if getattr(settings, 'ollama_base_url', None):
            vlm_sources.append('ollama')

        # 檢查 OpenAI
        if getattr(settings, 'openai_api_key', None) and str(settings.openai_api_key).startswith('sk-'):
            vlm_sources.append('openai')

        return len(vlm_sources) > 0

    def _check_database_connections(self) -> Dict[str, bool]:
        """檢查數據庫連接狀態"""
        connections = {}

        # 檢查 Neo4j
        connections['neo4j'] = self._check_neo4j_connection()

        # 檢查 Supabase
        connections['supabase'] = self._check_supabase_connection()

        return connections

    def _check_neo4j_connection(self) -> bool:
        """檢查 Neo4j 連接"""
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            driver.verify_connectivity()
            driver.close()
            return True
        except Exception:
            return False

    def _check_supabase_connection(self) -> bool:
        """檢查 Supabase 連接"""
        try:
            from supabase import create_client
            client = create_client(settings.supabase_url, settings.supabase_key)
            # 簡單的連接測試
            storage = client.storage
            return True
        except Exception:
            return False

    def _check_embedding_service(self) -> bool:
        """檢查嵌入服務狀態"""
        try:
            from grag.ingestion.indexing.providers.embedding_providers import create_embedding_provider
            provider = create_embedding_provider()
            return provider.is_available()
        except Exception:
            return False

    def _assess_overall_health(self, status: Dict[str, Any]) -> str:
        """評估總體系統健康度"""
        healthy_components = 0
        total_components = 0

        # 計算可用組件
        components_to_check = [
            status.get('langchain', False),
            status.get('database', {}).get('neo4j', False),
            status.get('database', {}).get('supabase', False),
            status.get('embedding_service', False)
        ]

        healthy_components = sum(components_to_check)
        total_components = len(components_to_check)

        # VLM 配置是可選的，不計入總體健康度
        health_ratio = healthy_components / total_components

        if health_ratio >= 0.8:
            return 'excellent'
        elif health_ratio >= 0.6:
            return 'good'
        elif health_ratio >= 0.3:
            return 'fair'
        else:
            return 'poor'

    def get_service_details(self, service_name: str) -> Dict[str, Any]:
        """獲取特定服務的詳細資訊"""
        service_details = {
            'langchain': {
                'name': 'LangChain',
                'description': '核心NLP處理框架',
                'importance': 'critical'
            },
            'neo4j': {
                'name': 'Neo4j',
                'description': '知識圖譜數據庫',
                'importance': 'critical'
            },
            'supabase': {
                'name': 'Supabase',
                'description': '向量數據庫',
                'importance': 'critical'
            },
            'embedding_service': {
                'name': '嵌入服務',
                'description': '文字向量化服務',
                'importance': 'high'
            }
        }

        return service_details.get(service_name, {})

    def _get_timestamp(self) -> str:
        """獲取當前時間戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def create_health_report(self) -> Dict[str, Any]:
        """創建完整的健康報告"""
        status = self.get_system_status()

        report = {
            'timestamp': status['timestamp'],
            'overall_health': status['overall_health'],
            'services': {},
            'recommendations': []
        }

        # 服務詳細狀態
        for service_name, service_status in status.items():
            if service_name not in ['timestamp', 'overall_health']:
                if isinstance(service_status, dict):
                    # 處理嵌套狀態（如 database）
                    for sub_service, sub_status in service_status.items():
                        report['services'][sub_service] = {
                            'status': 'healthy' if sub_status else 'unhealthy',
                            'details': self.get_service_details(sub_service)
                        }
                else:
                    report['services'][service_name] = {
                        'status': 'healthy' if service_status else 'unhealthy',
                        'details': self.get_service_details(service_name)
                    }

        # 生成建議
        report['recommendations'] = self._generate_recommendations(status)

        return report

    def _generate_recommendations(self, status: Dict[str, Any]) -> list:
        """生成健康建議"""
        recommendations = []

        # 檢查關鍵服務
        if not status.get('langchain', False):
            recommendations.append("安裝 LangChain 框架以獲得最佳處理品質")

        if not status.get('database', {}).get('neo4j', False):
            recommendations.append("檢查 Neo4j 數據庫連接設置")

        if not status.get('database', {}).get('supabase', False):
            recommendations.append("檢查 Supabase 向量數據庫連接設置")

        if not status.get('embedding_service', False):
            recommendations.append("配置嵌入服務以支持向量搜索功能")

        if not status.get('vlm_configured', False):
            recommendations.append("配置 VLM 服務 (Ollama/OpenAI) 提升視覺處理能力")

        if not recommendations:
            recommendations.append("所有系統服務運作正常，享受完整功能！")

        return recommendations

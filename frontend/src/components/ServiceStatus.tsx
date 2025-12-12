'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Database,
  Server,
  Wifi,
  WifiOff,
  Eye,
  MessageSquare,
  Cpu
} from 'lucide-react';
import { apiService } from '@/services/api';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  description: string;
  icon: React.ComponentType<any>;
  lastChecked: Date | null;
}

export function ServiceStatus() {
  const [services, setServices] = useState<ServiceStatus[]>([
    {
      name: '後端API',
      status: 'unknown',
      description: 'GraphRAG API服務',
      icon: Server,
      lastChecked: null
    },
    {
      name: 'Neo4j資料庫',
      status: 'unknown',
      description: '圖資料庫連接',
      icon: Database,
      lastChecked: null
    },
    {
      name: 'Supabase向量庫',
      status: 'unknown',
      description: '向量資料庫連接',
      icon: Database,
      lastChecked: null
    },
    {
      name: 'VLM服務',
      status: 'unknown',
      description: '視覺語言模型 (Ollama qwen3-vl)',
      icon: Eye,
      lastChecked: null
    },
    {
      name: 'LLM服務',
      status: 'unknown',
      description: '大語言模型服務',
      icon: MessageSquare,
      lastChecked: null
    },
    {
      name: '嵌入服務',
      status: 'unknown',
      description: '文字向量化服務',
      icon: Cpu,
      lastChecked: null
    },
    {
      name: '網路連接',
      status: 'unknown',
      description: '前端到後端連接',
      icon: Wifi,
      lastChecked: null
    }
  ]);

  const [checking, setChecking] = useState(false);

  const checkServices = async () => {
    setChecking(true);

    try {
      // Check backend health
      const healthResponse = await apiService.getHealth();

      // Update services status based on health response
      setServices(prev => prev.map(service => {
        const now = new Date();

        switch (service.name) {
          case '後端API':
            return {
              ...service,
              status: healthResponse.status === 'healthy' ? 'healthy' : 'unhealthy',
              lastChecked: now
            };

          case 'Neo4j資料庫':
            return {
              ...service,
              status: healthResponse.services?.database?.neo4j ? 'healthy' : 'unhealthy',
              lastChecked: now
            };

          case 'Supabase向量庫':
            return {
              ...service,
              status: healthResponse.services?.database?.supabase ? 'healthy' : 'unhealthy',
              lastChecked: now
            };

          case 'VLM服務':
            return {
              ...service,
              status: healthResponse.services?.vlm_service?.available ? 'healthy' : 'unhealthy',
              lastChecked: now
            };

          case 'LLM服務':
            return {
              ...service,
              status: healthResponse.services?.llm_service?.available ? 'healthy' : 'unhealthy',
              lastChecked: now
            };

          case '嵌入服務':
            return {
              ...service,
              status: healthResponse.services?.embedding_service ? 'healthy' : 'unhealthy',
              lastChecked: now
            };

          case '網路連接':
            return {
              ...service,
              status: 'healthy', // If we got here, network is working
              lastChecked: now
            };

          default:
            return { ...service, lastChecked: now };
        }
      }));

    } catch (error) {
      console.error('Failed to check services:', error);

      // Mark all services as unhealthy on network error
      setServices(prev => prev.map(service => ({
        ...service,
        status: 'unhealthy',
        lastChecked: new Date()
      })));
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkServices();

    // Check every 30 seconds
    const interval = setInterval(checkServices, 30000);

    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'unhealthy':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'unhealthy':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    }
  };

  const getStatusText = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'healthy':
        return '正常';
      case 'unhealthy':
        return '異常';
      default:
        return '未知';
    }
  };

  const overallStatus = services.every(s => s.status === 'healthy') ? 'healthy' :
                       services.some(s => s.status === 'unhealthy') ? 'unhealthy' : 'unknown';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Server className="w-5 h-5" />
            服務狀態
            <Badge
              variant={overallStatus === 'healthy' ? 'default' : 'destructive'}
              className="ml-2"
            >
              {getStatusText(overallStatus)}
            </Badge>
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={checkServices}
            disabled={checking}
            className="flex items-center gap-1"
          >
            <RefreshCw className={`w-4 h-4 ${checking ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {services.map((service) => {
            const Icon = service.icon;
            return (
              <div
                key={service.name}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5 text-gray-500" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{service.name}</span>
                      {getStatusIcon(service.status)}
                    </div>
                    <p className="text-sm text-gray-500">{service.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge className={getStatusColor(service.status)}>
                    {getStatusText(service.status)}
                  </Badge>
                  {service.lastChecked && (
                    <span className="text-xs text-gray-400">
                      {service.lastChecked.toLocaleTimeString('zh-CN')}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-blue-900 dark:text-blue-100">狀態說明</p>
              <ul className="mt-1 text-blue-800 dark:text-blue-200 space-y-1">
                <li>• 每30秒自動檢查服務狀態</li>
                <li>• 點擊「刷新」按鈕可手動檢查</li>
                <li>• VLM/LLM服務為可選，影響視覺處理功能</li>
                <li>• 核心服務（API/資料庫）正常時基本功能可用</li>
                <li>• 所有服務正常時系統功能最完整</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

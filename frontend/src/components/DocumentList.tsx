'use client';

import React, { useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FileText, Trash2, RefreshCw, Clock, Database } from 'lucide-react';
import { apiService } from '@/services/api';

interface Document {
  document_id: string;
  title: string;
  source_path: string;
  created_at: string;
  updated_at: string;
  chunk_count: number;
  vector_count: number;
  processing_status?: string;
  processing_method?: string;
  processing_quality?: string;
  content_quality_score?: number;
  vlm_provider?: string;
  vlm_success?: boolean;
  total_characters?: number;
}

export interface DocumentListRef {
  refreshDocuments: () => void;
}

export const DocumentList = forwardRef<DocumentListRef>((props, ref) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.listDocuments(50, 0);
      // API直接返回documents和pagination，沒有success字段
      setDocuments(response.documents || []);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
      setError('網路錯誤，無法獲取文檔列表');
    } finally {
      setLoading(false);
    }
  };

  // 暴露refreshDocuments方法給父組件
  useImperativeHandle(ref, () => ({
    refreshDocuments: fetchDocuments
  }));

  const deleteDocument = async (documentId: string, title: string) => {
    if (!confirm(`確定要刪除文檔 "${title}" 嗎？此操作無法撤銷。`)) {
      return;
    }

    try {
      const response = await apiService.deleteDocument(documentId);
      if (response.success) {
        // 重新獲取文檔列表
        await fetchDocuments();
      } else {
        alert('刪除文檔失敗');
      }
    } catch (err) {
      console.error('Failed to delete document:', err);
      alert('刪除文檔時發生錯誤');
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString('zh-CN');
    } catch {
      return dateString;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '未知';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            已上傳文檔
            <Badge variant="outline">
              {documents.length} 個文檔
            </Badge>
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchDocuments}
            disabled={loading}
            className="flex items-center gap-1"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {loading && documents.length === 0 && (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 animate-spin mr-2" />
            <span>載入中...</span>
          </div>
        )}

        {documents.length === 0 && !loading && !error && (
          <div className="text-center py-8 text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>尚未上傳任何文檔</p>
            <p className="text-sm mt-2">請使用「文件上傳」功能上傳文檔</p>
          </div>
        )}

        {documents.length > 0 && (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.document_id}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                      {doc.title}
                    </h3>
                    <Badge
                      variant={doc.processing_status === 'completed' ? 'default' : 'secondary'}
                      className="text-xs"
                    >
                      {doc.processing_status === 'completed' ? '已完成' : '處理中'}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-500 mb-2">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(doc.created_at)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Database className="w-3 h-3" />
                      {doc.chunk_count} 個片段, {doc.vector_count || 0} 個向量
                    </span>
                    {doc.total_characters && (
                      <span>
                        {doc.total_characters.toLocaleString()} 字符
                      </span>
                    )}
                  </div>

                  {/* Processing Method Information */}
                  {(doc.processing_method || doc.vlm_provider) && (
                    <div className="flex items-center gap-2 mb-2">
                      {doc.processing_method && (
                        <Badge variant="outline" className="text-xs">
                          處理方法: {doc.processing_method}
                        </Badge>
                      )}
                      {doc.vlm_provider && (
                        <Badge variant="outline" className="text-xs">
                          VLM: {doc.vlm_provider}
                        </Badge>
                      )}
                      {doc.processing_quality && (
                        <Badge
                          variant={doc.processing_quality === '高品質' ? 'default' : 'secondary'}
                          className="text-xs"
                        >
                          {doc.processing_quality}
                        </Badge>
                      )}
                    </div>
                  )}

                  {/* Quality Score */}
                  {doc.content_quality_score !== undefined && (
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs text-gray-500">內容品質分數:</span>
                      <div className="flex items-center gap-1">
                        <div className="w-16 h-2 bg-gray-200 rounded">
                          <div
                            className={`h-2 rounded ${
                              doc.content_quality_score > 0.7 ? 'bg-green-500' :
                              doc.content_quality_score > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${doc.content_quality_score * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600">
                          {(doc.content_quality_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-gray-400 mt-1 truncate">
                    {doc.source_path}
                  </p>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteDocument(doc.document_id, doc.title)}
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
});

DocumentList.displayName = 'DocumentList';

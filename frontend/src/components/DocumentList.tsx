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
  file_size: number;
  processing_status: string;
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
      if (response.success) {
        setDocuments(response.documents);
      } else {
        setError('獲取文檔列表失敗');
      }
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

                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(doc.created_at)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Database className="w-3 h-3" />
                      {doc.chunk_count} 個片段
                    </span>
                    {doc.file_size > 0 && (
                      <span>
                        {formatFileSize(doc.file_size)}
                      </span>
                    )}
                  </div>

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

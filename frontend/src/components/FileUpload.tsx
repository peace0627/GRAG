'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Upload, File, X, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { apiService } from '@/services/api';

interface ProcessingStep {
  stage: string;
  module: string;
  method: string;
  description: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  timestamp?: Date;
}

interface UploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  processingSteps?: ProcessingStep[];
  processingTrace?: any;
  uploadResponse?: any;
}

const SUPPORTED_FORMATS = ['pdf', 'docx', 'jpg', 'jpeg', 'png'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

interface FileUploadProps {
  onUploadSuccess?: () => void;
}

export function FileUpload({ onUploadSuccess }: FileUploadProps = {}) {
  const [uploads, setUploads] = useState<UploadProgress[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [filesToUpload, setFilesToUpload] = useState<UploadProgress[]>([]);
  const [expandedUpload, setExpandedUpload] = useState<number | null>(null);

  const validateFile = (file: File): string | null => {
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!extension || !SUPPORTED_FORMATS.includes(extension)) {
      return `不支持的文件格式。支持的格式: ${SUPPORTED_FORMATS.join(', ')}`;
    }
    if (file.size > MAX_FILE_SIZE) {
      return `文件大小超過限制。最大允許: ${MAX_FILE_SIZE / 1024 / 1024}MB`;
    }
    return null;
  };

  // 處理文件選擇
  const handleFileSelect = useCallback((files: FileList | null) => {
    console.log('[FileUpload] File select triggered:', files);
    if (!files || files.length === 0) {
      console.log('[FileUpload] No files selected');
      return;
    }

    const newUploads: UploadProgress[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      console.log('[FileUpload] Processing file:', file.name, file.size, file.type);
      const error = validateFile(file);
      if (error) {
        console.log('[FileUpload] File validation error:', error);
        newUploads.push({
          file,
          progress: 0,
          status: 'error',
          error
        });
      } else {
        console.log('[FileUpload] File validated successfully');
        newUploads.push({
          file,
          progress: 0,
          status: 'pending'
        });
      }
    }

    console.log('[FileUpload] New uploads:', newUploads);
    setUploads(prev => [...prev, ...newUploads]);
    setFilesToUpload(newUploads);
  }, []);

  // 處理文件上傳
  const uploadFile = useCallback(async (upload: UploadProgress, index: number) => {
    console.log('Starting upload for:', upload.file.name);

    // 初始化處理步驟
    const initialSteps: ProcessingStep[] = [
      { stage: '文件驗證', module: '前端驗證', method: 'validateFile()', description: '檢查文件格式和大小', status: 'completed', timestamp: new Date() },
      { stage: '文件載入', module: 'LangChain', method: 'load()', description: '讀取並解析文件內容', status: 'pending' },
      { stage: '文檔處理', module: 'VLM/OCR', method: 'process_document()', description: '執行視覺或文本處理', status: 'pending' },
      { stage: '分塊處理', module: 'LlamaIndex', method: 'get_nodes_from_documents()', description: '將文檔分割為文本片段', status: 'pending' },
      { stage: '向量嵌入', module: 'SentenceTransformers', method: 'encode()', description: '生成文本向量表示', status: 'pending' },
      { stage: '知識提取', module: 'NER Extractor', method: 'extract_entities()', description: '識別實體和關係', status: 'pending' },
      { stage: 'Neo4j 存儲', module: 'Neo4j Graph DB', method: 'create_document_sync()', description: '保存文檔和分塊到圖資料庫', status: 'pending' },
      { stage: 'Supabase 存儲', module: 'Supabase pgvector', method: 'insert_vector_record()', description: '保存向量到向量資料庫', status: 'pending' }
    ];

    // 更新狀態為上傳中
    setUploads(prev => prev.map((u, i) =>
      i === index ? {
        ...u,
        status: 'uploading' as const,
        progress: 10,
        processingSteps: initialSteps
      } : u
    ));

    try {
      console.log('Calling API upload...');
      const response = await apiService.uploadSingleFile(upload.file);
      console.log('Upload response:', response);

      // 從API響應中提取處理步驟信息
      const processingTrace = response.processing_trace;
      const strategy = response.strategy_used;
      const statistics = response.statistics;

      // 更新處理步驟狀態
      const updatedSteps = initialSteps.map(step => {
        let newStatus: ProcessingStep['status'] = 'completed';
        let description = step.description;

        // 根據API響應更新具體的處理信息
        if (step.stage === '文檔處理' && strategy) {
          if (strategy.vlm_success) {
            description = `使用 ${strategy.vlm_provider || 'VLM'} 處理文檔`;
          } else if (strategy.processing_layer) {
            const layerMap: { [key: string]: string } = {
              'MinerU': '使用 MinerU PDF解析器處理',
              'OCR': '使用 OCR 文字辨識處理',
              'FALLBACK_TEXT_PROCESSING': '使用結構化文字分析處理'
            };
            description = layerMap[strategy.processing_layer] || step.description;
          }
        }

        if (step.stage === '分塊處理' && statistics?.chunks) {
          description = `創建 ${statistics.chunks.total} 個文本片段`;
        }

        if (step.stage === '向量嵌入' && statistics?.embeddings) {
          description = `生成 ${statistics.embeddings.created} 個 ${statistics.embeddings.dimension} 維向量`;
        }

        if (step.stage === '知識提取' && statistics?.knowledge) {
          description = `提取 ${statistics.knowledge.entities} 個實體和 ${statistics.knowledge.relations} 個關係`;
        }

        if (step.stage === 'Neo4j 存儲' && response.stage_results?.neo4j) {
          const neo4j = response.stage_results.neo4j;
          if (neo4j.success) {
            description = `成功保存到 Neo4j (${neo4j.chunks_created || 0} 個文檔片段)`;
          } else {
            newStatus = 'failed';
            description = `Neo4j 保存失敗: ${neo4j.error || '未知錯誤'}`;
          }
        }

        if (step.stage === 'Supabase 存儲' && response.stage_results?.pgvector) {
          const pgvector = response.stage_results.pgvector;
          if (pgvector.success) {
            description = `成功保存到 Supabase (${pgvector.vectors_ingested || 0} 個向量)`;
          } else {
            newStatus = 'failed';
            description = `Supabase 保存失敗: ${pgvector.error || '未知錯誤'}`;
          }
        }

        return {
          ...step,
          description,
          status: newStatus,
          timestamp: new Date()
        };
      });

      // 更新為成功狀態
      setUploads(prev => prev.map((u, i) =>
        i === index ? {
          ...u,
          status: 'success' as const,
          progress: 100,
          processingSteps: updatedSteps,
          processingTrace,
          uploadResponse: response.data
        } : u
      ));

      console.log('Upload successful');

      // 調用成功回調函數
      if (onUploadSuccess) {
        onUploadSuccess();
      }

    } catch (error) {
      console.error('Upload failed:', error);
      const errorMessage = apiService.getErrorMessage(error as any);

      // 更新處理步驟為失敗
      const failedSteps = initialSteps.map(step => ({
        ...step,
        status: 'failed' as const,
        timestamp: new Date()
      }));

      // 更新為錯誤狀態
      setUploads(prev => prev.map((u, i) =>
        i === index ? {
          ...u,
          status: 'error' as const,
          progress: 0,
          error: errorMessage,
          processingSteps: failedSteps
        } : u
      ));
    }
  }, [onUploadSuccess]);

  // 當有新文件時開始上傳
  useEffect(() => {
    if (filesToUpload.length > 0) {
      console.log('Starting uploads for files:', filesToUpload.length);
      filesToUpload.forEach((upload, idx) => {
        if (upload.status !== 'error') {
          const globalIndex = uploads.length - filesToUpload.length + idx;
          uploadFile(upload, globalIndex);
        }
      });
      setFilesToUpload([]);
    }
  }, [filesToUpload, uploads.length, uploadFile]);

  const removeUpload = (index: number) => {
    setUploads(prev => prev.filter((_, i) => i !== index));
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const getStatusIcon = (status: UploadProgress['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'uploading':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      default:
        return <File className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: UploadProgress['status']) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'uploading':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            文件上傳
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragOver
                ? 'border-blue-400 bg-blue-50 dark:bg-blue-950'
                : 'border-gray-300 dark:border-gray-600'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <div className="space-y-2">
              <p className="text-lg font-medium">
                拖拽文件到這裡，或點擊選擇文件
              </p>
              <p className="text-sm text-gray-500">
                支持格式: PDF, DOCX, JPG, PNG (最大 10MB)
              </p>
            </div>
            <input
              ref={(input) => {
                // Store reference for direct click access
                if (input) {
                  (input as any)._fileInput = input;
                }
              }}
              type="file"
              multiple
              accept=".pdf,.docx,.jpg,.jpeg,.png"
              className="hidden"
              id="file-upload"
              onChange={(e) => handleFileSelect(e.target.files)}
            />
            <Button
              className="mt-4"
              variant="outline"
              onClick={() => {
                const input = document.getElementById('file-upload') as HTMLInputElement;
                if (input) {
                  input.click();
                }
              }}
            >
              選擇文件
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Upload Progress */}
      {uploads.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>上傳進度</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {uploads.map((upload, index) => (
                <div key={index}>
                  <div className="flex items-center space-x-4 p-4 border rounded-lg">
                    <div className="flex-shrink-0">
                      {getStatusIcon(upload.status)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {upload.file.name}
                        </p>
                        <p className="text-sm text-gray-500">
                          {(upload.file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>

                      {upload.status === 'uploading' && (
                        <Progress value={upload.progress} className="mt-2" />
                      )}

                      {upload.status === 'error' && upload.error && (
                        <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                          {upload.error}
                        </p>
                      )}

                      {upload.status === 'success' && (
                        <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                          上傳成功
                        </p>
                      )}
                    </div>

                    <div className="flex-shrink-0">
                      <Badge className={getStatusColor(upload.status)}>
                        {upload.status === 'pending' && '等待中'}
                        {upload.status === 'uploading' && '上傳中'}
                        {upload.status === 'success' && '成功'}
                        {upload.status === 'error' && '失敗'}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {upload.processingSteps && upload.processingSteps.length > 0 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setExpandedUpload(expandedUpload === index ? null : index)}
                          className="flex items-center gap-1"
                        >
                          {expandedUpload === index ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                          詳情
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeUpload(index)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Processing Steps Details */}
                  {expandedUpload === index && upload.processingSteps && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                        處理流程詳情
                      </h4>
                      <div className="space-y-2">
                        {upload.processingSteps.map((step, stepIndex) => (
                          <div
                            key={stepIndex}
                            className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                          >
                            <div className="flex-shrink-0 mt-0.5">
                              {step.status === 'completed' && (
                                <CheckCircle className="w-4 h-4 text-green-500" />
                              )}
                              {step.status === 'processing' && (
                                <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                              )}
                              {step.status === 'failed' && (
                                <AlertCircle className="w-4 h-4 text-red-500" />
                              )}
                              {step.status === 'pending' && (
                                <div className="w-4 h-4 border-2 border-gray-300 rounded-full"></div>
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                  {step.stage}
                                </span>
                                <Badge
                                  variant="outline"
                                  className="text-xs"
                                >
                                  {step.module}
                                </Badge>
                              </div>
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                {step.description}
                              </p>
                              {step.method && (
                                <code className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">
                                  {step.method}
                                </code>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

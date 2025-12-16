// GraphRAG API Service Layer
import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  QueryRequest,
  QueryResponse,
  HealthResponse,
  SystemStatusResponse,
  UploadResponse,
  ApiError
} from '@/types/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
      timeout: parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '120000'), // 增加到2分鐘
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        const apiError: ApiError = {
          detail: error.response?.data?.detail || error.message || 'Unknown error'
        };
        return Promise.reject(apiError);
      }
    );
  }

  // Health Check
  async getHealth(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }

  // System Status
  async getSystemStatus(): Promise<SystemStatusResponse> {
    const response = await this.client.get<SystemStatusResponse>('/system/status');
    return response.data;
  }

  // Query Methods
  async queryAgentic(queryData: QueryRequest): Promise<QueryResponse> {
    const response = await this.client.post<QueryResponse>('/query', queryData);
    return response.data;
  }

  async querySimple(queryData: QueryRequest): Promise<QueryResponse> {
    const response = await this.client.post<QueryResponse>('/query/simple', queryData);
    return response.data;
  }

  // File Upload
  async uploadSingleFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<UploadResponse>('/upload/single', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  // Async File Upload
  async uploadFileAsync(file: File): Promise<{
    success: boolean;
    task_id: string;
    message: string;
    file_size_mb: number;
  }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post('/upload/async', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  // Get Upload Task Status
  async getUploadStatus(taskId: string): Promise<{
    task_id: string;
    filename: string;
    status: string;
    progress: number;
    message: string;
    start_time?: string;
    end_time?: string;
    result?: any;
    error?: string;
    estimated_time?: number;
    elapsed_time: number;
  }> {
    const response = await this.client.get(`/upload/status/${taskId}`);
    return response.data;
  }

  // Cancel Upload Task
  async cancelUploadTask(taskId: string): Promise<{ success: boolean; message: string }> {
    const response = await this.client.delete(`/upload/cancel/${taskId}`);
    return response.data;
  }

  // List Upload Tasks
  async listUploadTasks(limit?: number): Promise<{
    success: boolean;
    tasks: any[];
    total: number;
  }> {
    const params = new URLSearchParams();
    if (limit !== undefined) params.append('limit', limit.toString());

    const response = await this.client.get(`/upload/tasks?${params.toString()}`);
    return response.data;
  }

  async uploadMultipleFiles(files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file, index) => {
      formData.append('files', file);
    });

    const response = await this.client.post<UploadResponse>('/upload/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  // Document Management
  async listDocuments(limit?: number, offset?: number): Promise<{
    documents: any[];
    pagination: { limit: number; offset: number; total: number };
  }> {
    const params = new URLSearchParams();
    if (limit !== undefined) params.append('limit', limit.toString());
    if (offset !== undefined) params.append('offset', offset.toString());

    const response = await this.client.get(`/documents?${params.toString()}`);
    return response.data;
  }

  async deleteDocument(documentId: string): Promise<{ success: boolean; message: string }> {
    const response = await this.client.delete(`documents/${documentId}`);
    return response.data;
  }

  async deleteMultipleDocuments(documentIds: string[]): Promise<{ success: boolean; message: string }> {
    const response = await this.client.delete('/documents/batch', {
      data: documentIds,
    });
    return response.data;
  }

  // Statistics
  async getStatistics(): Promise<any> {
    const response = await this.client.get('/statistics');
    return response.data;
  }

  // Utility methods
  isApiError(error: any): error is ApiError {
    return error && typeof error.detail !== 'undefined';
  }

  getErrorMessage(error: ApiError): string {
    if (typeof error.detail === 'string') {
      return error.detail;
    }

    if (Array.isArray(error.detail)) {
      return error.detail.map(err => err.msg || 'Unknown error').join(', ');
    }

    return 'An unknown error occurred';
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;

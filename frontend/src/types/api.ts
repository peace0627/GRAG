// GraphRAG API Type Definitions
// Generated from FastAPI schemas

export interface Evidence {
  source_type: string;
  content: string;
  confidence: number;
  metadata?: Record<string, any>;
}

export interface Reflection {
  context_sufficient: boolean;
  gaps_identified: string[];
  confidence_assessment: {
    overall: number;
  };
}

export interface QueryRequest {
  query: string;
  context?: Record<string, any>;
  max_evidence?: number;
}

export interface QueryResponse {
  query_id: string;
  original_query: string;
  query_type: 'factual' | 'analytical' | 'visual' | 'temporal' | 'complex';
  final_answer: string;
  confidence_score: number;
  evidence_count: number;
  execution_time: number;
  needs_clarification: boolean;
  clarification_questions?: string[];
  planning_info?: any;
  evidence: Evidence[];
  reflection: Reflection;
  success: boolean;
  error?: string;
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  overall_health: 'excellent' | 'good' | 'fair' | 'poor';
  services: Record<string, any>;
}

export interface SystemStatusResponse {
  status: 'operational' | 'degraded' | 'down';
  timestamp: string;
  overall_health: 'excellent' | 'good' | 'fair' | 'poor';
  services: Record<string, any>;
  agents?: {
    status: string;
    agents: Record<string, string>;
    tools_available: number;
    database_status: Record<string, any>;
    llm_model: string;
  };
}

export interface UploadResponse {
  success: boolean;
  message: string;
  document_id?: string;
  file_id?: string;
  file_path?: string;
  processing_time?: number;
  error?: string;
  data?: any;
  processing_trace?: any;
  strategy_used?: any;
  statistics?: any;
  stage_results?: any;
  metadata?: any;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  size: number;
  uploaded_at: string;
  status: 'processing' | 'completed' | 'failed';
}

// API Error Types
export interface ApiError {
  detail: string | Array<{
    type: string;
    loc: string[];
    msg: string;
    input: any;
  }>;
}

// Query Types for UI
export type QueryStatus = 'idle' | 'loading' | 'success' | 'error';

export interface QueryState {
  status: QueryStatus;
  data?: QueryResponse;
  error?: string;
  isLoading: boolean;
}

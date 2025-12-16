'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Send, Brain, Eye, Search, Clock } from 'lucide-react';
import { QueryResponse, QueryStatus } from '@/types/api';
import { apiService } from '@/services/api';
import { ReasoningTrace } from './ReasoningTrace';
import { Markdown } from '@/components/ui/markdown';

export function QueryInterface() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<QueryStatus>('idle');
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [showReasoningTrace, setShowReasoningTrace] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!query.trim()) return;

    setStatus('loading');
    setError('');
    setResult(null);

    try {
      const response = await apiService.queryAgentic({ query: query.trim() });
      setResult(response);
      setStatus('success');
    } catch (err) {
      setError(apiService.getErrorMessage(err as any));
      setStatus('error');
    }
  };

  const getQueryTypeIcon = (type: string) => {
    switch (type) {
      case 'visual':
        return <Eye className="w-4 h-4" />;
      case 'analytical':
        return <Brain className="w-4 h-4" />;
      case 'temporal':
        return <Clock className="w-4 h-4" />;
      default:
        return <Search className="w-4 h-4" />;
    }
  };

  const getQueryTypeColor = (type: string) => {
    switch (type) {
      case 'visual':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'analytical':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'temporal':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Query Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            輸入您的查詢
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Textarea
              placeholder="例如：圖表顯示哪個月銷售最低？或者系統支持哪些數據庫？"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="min-h-24 resize-none"
              disabled={status === 'loading'}
            />
            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={!query.trim() || status === 'loading'}
                className="flex items-center gap-2"
              >
                {status === 'loading' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    處理中...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    發送查詢
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Results */}
      {status === 'loading' && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-8">
              <div className="flex items-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-slate-600" />
                <span className="text-slate-600">正在分析查詢並檢索相關信息...</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {status === 'error' && (
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardContent className="pt-6">
            <div className="text-red-800 dark:text-red-200">
              <h3 className="font-semibold mb-2">查詢失敗</h3>
              <p>{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {status === 'success' && result && (
        <div className="space-y-4">
          {/* Query Metadata */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  {getQueryTypeIcon(result.query_type)}
                  查詢結果
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Badge className={getQueryTypeColor(result.query_type)}>
                    {result.query_type}
                  </Badge>
                  <Badge variant="outline">
                    信心度: {Math.round(result.confidence_score * 100)}%
                  </Badge>
                  <Badge variant="outline">
                    {result.execution_time.toFixed(2)}s
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Answer */}
              <div>
                <h4 className="font-semibold text-lg mb-2">回答</h4>
                <Markdown content={result.final_answer} />
              </div>

              {/* Evidence */}
              {result.evidence.length > 0 && (
                <div>
                  <h4 className="font-semibold text-lg mb-2">證據來源</h4>
                  <div className="space-y-2">
                    {result.evidence.slice(0, 3).map((evidence, index) => (
                      <div key={index} className="bg-slate-50 dark:bg-slate-800 rounded p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                            {evidence.source_type}
                          </span>
                          <Badge variant="secondary" className="text-xs">
                            信心度: {Math.round(evidence.confidence * 100)}%
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-700 dark:text-slate-300">
                          {evidence.content.length > 200
                            ? `${evidence.content.substring(0, 200)}...`
                            : evidence.content
                          }
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Clarification Questions */}
              {result.needs_clarification && result.clarification_questions && (
                <div className="bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded p-4">
                  <h4 className="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">
                    需要澄清的問題
                  </h4>
                  <ul className="list-disc list-inside space-y-1">
                    {result.clarification_questions.map((question, index) => (
                      <li key={index} className="text-yellow-700 dark:text-yellow-300 text-sm">
                        {question}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Agent Reasoning Trace */}
          <ReasoningTrace
            queryResult={result}
            isExpanded={showReasoningTrace}
            onToggle={() => setShowReasoningTrace(!showReasoningTrace)}
          />
        </div>
      )}
    </div>
  );
}

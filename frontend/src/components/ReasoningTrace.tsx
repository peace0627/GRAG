'use client';

import React, { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp, CheckCircle, Brain, Search, Zap } from 'lucide-react';
import { QueryResponse } from '@/types/api';

interface ReasoningTraceProps {
  queryResult: QueryResponse | null;
  isExpanded: boolean;
  onToggle: () => void;
}

interface Step {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<any>;
  status: 'completed' | 'error';
  details: string[];
}

export function ReasoningTrace({ queryResult, isExpanded, onToggle }: ReasoningTraceProps) {
  const steps = useMemo<Step[]>(() => {
    if (!queryResult) return [];

    const steps: Step[] = [
      {
        id: 'input',
        title: '用戶查詢',
        description: queryResult.original_query.length > 60
          ? `${queryResult.original_query.substring(0, 60)}...`
          : queryResult.original_query,
        icon: Search,
        status: 'completed',
        details: []
      },
      {
        id: 'classification',
        title: '查詢分類',
        description: `類型: ${queryResult.query_type}`,
        icon: Brain,
        status: 'completed',
        details: [
          `信心度: ${Math.round(queryResult.confidence_score * 100)}%`,
          `執行時間: ${queryResult.execution_time.toFixed(2)}秒`
        ]
      }
    ];

    // 添加規劃階段
    if (queryResult.planning_info) {
      steps.push({
        id: 'planning',
        title: '查詢規劃',
        description: `規劃 ${queryResult.planning_info.execution_plan_steps} 個步驟`,
        icon: Brain,
        status: 'completed',
        details: queryResult.planning_info.suggested_tools.slice(0, 2)
      });
    }

    // 添加檢索階段
    steps.push({
      id: 'retrieval',
      title: '多模態檢索',
      description: `找到 ${queryResult.evidence_count} 條證據`,
      icon: Search,
      status: 'completed',
      details: ['向量搜索', '圖譜遍歷', '證據融合']
    });

    // 添加推理階段
    if (queryResult.reflection) {
      steps.push({
        id: 'reasoning',
        title: '知識推理',
        description: queryResult.reflection.context_sufficient ? '上下文充足' : '發現知識差距',
        icon: Zap,
        status: 'completed',
        details: queryResult.reflection.gaps_identified.length > 0
          ? [`差距: ${queryResult.reflection.gaps_identified.join(', ')}`]
          : ['推理完成']
      });
    }

    // 添加最終答案
    const outputStatus = queryResult.success ? 'completed' : 'error';
    steps.push({
      id: 'output',
      title: '最終答案',
      description: queryResult.final_answer.length > 80
        ? `${queryResult.final_answer.substring(0, 80)}...`
        : queryResult.final_answer,
      icon: CheckCircle,
      status: outputStatus,
      details: queryResult.needs_clarification
        ? ['需要澄清']
        : ['答案生成完成']
    });

    return steps;
  }, [queryResult]);

  if (!queryResult) {
    return null;
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5" />
            Agent推理追蹤
            <Badge variant="outline" className="ml-2">
              {queryResult.execution_time.toFixed(2)}s
            </Badge>
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggle}
            className="flex items-center gap-1"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                收起
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                展開
              </>
            )}
          </Button>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent>
          {/* 推理流程圖 */}
          <div className="space-y-4">
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={step.id} className="flex items-start gap-4">
                  {/* 步驟節點 */}
                  <div className="flex-shrink-0">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      step.status === 'completed'
                        ? 'bg-green-100 border-2 border-green-300'
                        : 'bg-red-100 border-2 border-red-300'
                    }`}>
                      <Icon className={`w-5 h-5 ${
                        step.status === 'completed'
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`} />
                    </div>
                    {index < steps.length - 1 && (
                      <div className="w-0.5 h-8 bg-gray-300 mx-auto mt-2"></div>
                    )}
                  </div>

                  {/* 步驟內容 */}
                  <div className="flex-1 pb-8">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-semibold text-gray-900">{step.title}</h4>
                      <Badge variant="outline" className="text-xs">
                        {step.status === 'completed' ? '完成' : '錯誤'}
                      </Badge>
                    </div>
                    <p className="text-gray-700 mb-2">{step.description}</p>
                    {step.details.length > 0 && (
                      <div className="space-y-1">
                        {step.details.map((detail, detailIndex) => (
                          <div key={detailIndex} className="text-sm bg-gray-50 rounded px-3 py-1 text-gray-600">
                            {detail}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 推理統計 */}
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
            <div className="bg-blue-50 p-3 rounded-lg">
              <div className="text-sm font-medium text-blue-900">查詢類型</div>
              <div className="text-lg font-bold text-blue-700 capitalize">
                {queryResult.query_type}
              </div>
            </div>
            <div className="bg-green-50 p-3 rounded-lg">
              <div className="text-sm font-medium text-green-900">信心度</div>
              <div className="text-lg font-bold text-green-700">
                {Math.round(queryResult.confidence_score * 100)}%
              </div>
            </div>
            <div className="bg-purple-50 p-3 rounded-lg">
              <div className="text-sm font-medium text-purple-900">證據數量</div>
              <div className="text-lg font-bold text-purple-700">
                {queryResult.evidence_count}
              </div>
            </div>
            <div className="bg-orange-50 p-3 rounded-lg">
              <div className="text-sm font-medium text-orange-900">執行時間</div>
              <div className="text-lg font-bold text-orange-700">
                {queryResult.execution_time.toFixed(2)}s
              </div>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

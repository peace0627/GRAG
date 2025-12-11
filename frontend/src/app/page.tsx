'use client';

import { useState, useRef } from 'react';
import { QueryInterface } from '@/components/QueryInterface';
import { FileUpload } from '@/components/FileUpload';
import { KnowledgeGraph } from '@/components/KnowledgeGraph';
import { DocumentList, DocumentListRef } from '@/components/DocumentList';
import { ServiceStatus } from '@/components/ServiceStatus';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Search, Upload, Brain, Eye, BarChart3, FileText, Server, Activity } from 'lucide-react';

type TabType = 'query' | 'upload' | 'graph' | 'status';

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>('query');
  const [showKnowledgeGraph, setShowKnowledgeGraph] = useState(false);
  const documentListRef = useRef<DocumentListRef | null>(null);

  const tabs = [
    {
      id: 'query' as TabType,
      label: '智慧問答',
      icon: Search,
      description: '使用Agentic RAG進行智能查詢'
    },
    {
      id: 'upload' as TabType,
      label: '文件上傳',
      icon: Upload,
      description: '上傳文檔建立知識庫'
    },
    {
      id: 'graph' as TabType,
      label: '知識圖譜',
      icon: Eye,
      description: '探索知識圖譜結構'
    },
    {
      id: 'status' as TabType,
      label: '系統狀態',
      icon: Activity,
      description: '監控系統服務運行狀態'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-slate-900 dark:text-slate-100 mb-4">
            GraphRAG 智慧問答系統
          </h1>
          <p className="text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
            整合知識圖譜、視覺語言模型和Agentic RAG的企業級智能問答系統
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-4xl mx-auto mb-8">
          <div className="flex space-x-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <Button
                  key={tab.id}
                  variant={activeTab === tab.id ? 'default' : 'ghost'}
                  className="flex-1 flex items-center gap-2"
                  onClick={() => setActiveTab(tab.id)}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </Button>
              );
            })}
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto space-y-6">
          {activeTab === 'query' && <QueryInterface />}
          {activeTab === 'upload' && (
            <div className="space-y-6">
              <FileUpload
                onUploadSuccess={() => documentListRef.current?.refreshDocuments()}
              />
              <DocumentList ref={documentListRef} />
            </div>
          )}
          {activeTab === 'graph' && (
            <KnowledgeGraph
              queryResult={undefined}
              isExpanded={showKnowledgeGraph}
              onToggle={() => setShowKnowledgeGraph(!showKnowledgeGraph)}
            />
          )}
          {activeTab === 'status' && <ServiceStatus />}
        </div>

        {/* Feature Overview */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <Card className="bg-white dark:bg-slate-800 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-3">
                <Brain className="w-6 h-6 text-blue-600" />
                <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                  🤖 Agentic RAG
                </h3>
              </div>
              <p className="text-slate-600 dark:text-slate-400">
                自主查詢規劃和推理，多模態檢索和事實檢查
              </p>
            </CardContent>
          </Card>

          <Card className="bg-white dark:bg-slate-800 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-3">
                <Eye className="w-6 h-6 text-purple-600" />
                <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                  🎨 多模態理解
                </h3>
              </div>
              <p className="text-slate-600 dark:text-slate-400">
                處理PDF、圖片、圖表等多種格式，支持VLM視覺分析
              </p>
            </CardContent>
          </Card>

          <Card className="bg-white dark:bg-slate-800 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-3">
                <BarChart3 className="w-6 h-6 text-green-600" />
                <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                  🧠 知識圖譜
                </h3>
              </div>
              <p className="text-slate-600 dark:text-slate-400">
                Neo4j驅動的實體關係圖，動態知識連接和圖形查詢
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}

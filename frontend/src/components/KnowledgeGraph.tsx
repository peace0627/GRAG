'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import cytoscape from 'cytoscape';
// @ts-ignore
import dagre from 'cytoscape-dagre';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, ZoomIn, ZoomOut, RotateCcw, Search, Filter, Eye, EyeOff } from 'lucide-react';
import { apiService } from '@/services/api';

cytoscape.use(dagre);

interface GraphNode {
  id: string;
  label: string;
  type: 'entity' | 'event' | 'chunk' | 'visual_fact';
  properties?: Record<string, any>;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
}

interface KnowledgeGraphProps {
  queryResult?: any;
  isExpanded: boolean;
  onToggle: () => void;
}

export function KnowledgeGraph({ queryResult, isExpanded, onToggle }: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string>('all');
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);

  // 獲取圖譜數據
  const fetchGraphData = async () => {
    setLoading(true);
    try {
      // 從文檔列表生成圖譜數據
      const documentsResponse = await apiService.listDocuments(50, 0);

      if (documentsResponse.success && documentsResponse.documents.length > 0) {
        // 將文檔數據轉換為圖譜格式
        const graphData = await convertDocumentsToGraphData(documentsResponse.documents);
        setGraphData(graphData);
      } else {
        // 如果沒有文檔，使用空的圖譜
        setGraphData({ nodes: [], edges: [] });
      }
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
      // 出錯時使用空的圖譜
      setGraphData({ nodes: [], edges: [] });
    } finally {
      setLoading(false);
    }
  };

  // 將文檔數據轉換為圖譜數據
  const convertDocumentsToGraphData = async (documents: any[]) => {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];

    documents.forEach((doc, index) => {
      // 添加文檔節點
      nodes.push({
        id: doc.document_id,
        label: doc.title || `Document ${index + 1}`,
        type: 'entity',
        properties: {
          description: `Uploaded: ${new Date(doc.created_at).toLocaleString()}`,
          chunk_count: doc.chunk_count,
          source_path: doc.source_path
        }
      });

      // 如果有chunks，為每個chunk添加節點和關聯
      if (doc.chunk_count > 0) {
        for (let i = 0; i < Math.min(doc.chunk_count, 5); i++) { // 限制顯示的chunk數量
          const chunkId = `${doc.document_id}_chunk_${i}`;
          nodes.push({
            id: chunkId,
            label: `Chunk ${i + 1}`,
            type: 'chunk',
            properties: {
              content: `Text chunk from ${doc.title}`,
              order: i
            }
          });

          edges.push({
            id: `edge_${doc.document_id}_${chunkId}`,
            source: doc.document_id,
            target: chunkId,
            label: 'contains',
            type: 'contains'
          });
        }
      }
    });

    return { nodes, edges };
  };

  // 生成模擬圖譜數據 (用於演示)
  const generateMockGraphData = async (): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> => {
    // 模擬延遲
    await new Promise(resolve => setTimeout(resolve, 1000));

    const nodes: GraphNode[] = [
      { id: 'entity_1', label: 'GraphRAG', type: 'entity', properties: { description: '知識圖譜增強檢索' } },
      { id: 'entity_2', label: 'Neo4j', type: 'entity', properties: { description: '圖數據庫' } },
      { id: 'entity_3', label: 'Agentic RAG', type: 'entity', properties: { description: '自主檢索增強生成' } },
      { id: 'entity_4', label: 'VLM', type: 'entity', properties: { description: '視覺語言模型' } },
      { id: 'event_1', label: '數據處理', type: 'event', properties: { timestamp: '2024-01-01' } },
      { id: 'chunk_1', label: '技術文檔片段', type: 'chunk', properties: { content: '...' } },
      { id: 'visual_1', label: '架構圖', type: 'visual_fact', properties: { bbox: [0, 0, 100, 100] } },
    ];

    const edges: GraphEdge[] = [
      { id: 'edge_1', source: 'entity_1', target: 'entity_2', label: '使用', type: 'uses' },
      { id: 'edge_2', source: 'entity_1', target: 'entity_3', label: '實現', type: 'implements' },
      { id: 'edge_3', source: 'entity_3', target: 'entity_4', label: '集成', type: 'integrates' },
      { id: 'edge_4', source: 'entity_1', target: 'event_1', label: '參與', type: 'participates_in' },
      { id: 'edge_5', source: 'chunk_1', target: 'entity_1', label: '提及', type: 'mentions' },
      { id: 'edge_6', source: 'visual_1', target: 'entity_1', label: '描述', type: 'describes' },
    ];

    return { nodes, edges };
  };

  // 過濾節點和邊
  const filteredData = useMemo(() => {
    if (!graphData) return null;

    let filteredNodes = graphData.nodes;
    let filteredEdges = graphData.edges;

    // 根據搜索詞過濾
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filteredNodes = filteredNodes.filter(node =>
        node.label.toLowerCase().includes(searchLower) ||
        node.properties?.description?.toLowerCase().includes(searchLower)
      );

      // 只保留連接過濾後節點的邊
      const nodeIds = new Set(filteredNodes.map(n => n.id));
      filteredEdges = filteredEdges.filter(edge =>
        nodeIds.has(edge.source) && nodeIds.has(edge.target)
      );
    }

    // 根據節點類型過濾
    if (nodeTypeFilter !== 'all') {
      filteredNodes = filteredNodes.filter(node => node.type === nodeTypeFilter);

      const nodeIds = new Set(filteredNodes.map(n => n.id));
      filteredEdges = filteredEdges.filter(edge =>
        nodeIds.has(edge.source) && nodeIds.has(edge.target)
      );
    }

    return { nodes: filteredNodes, edges: filteredEdges };
  }, [graphData, searchTerm, nodeTypeFilter]);

  // 初始化Cytoscape圖譜
  useEffect(() => {
    if (!containerRef.current || !filteredData || !isExpanded) return;

    // 清理現有的實例
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // 創建Cytoscape實例
    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: [
        ...filteredData.nodes.map(node => ({
          data: {
            id: node.id,
            label: node.label,
            type: node.type,
            ...node.properties
          }
        })),
        ...filteredData.edges.map(edge => ({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            type: edge.type
          }
        }))
      ],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (ele: any) => {
              switch (ele.data('type')) {
                case 'entity': return '#3b82f6'; // blue
                case 'event': return '#10b981'; // green
                case 'chunk': return '#f59e0b'; // amber
                case 'visual_fact': return '#8b5cf6'; // violet
                default: return '#6b7280'; // gray
              }
            },
            'label': 'data(label)',
            'color': '#ffffff',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '12px',
            'font-weight': 'bold',
            'width': '60px',
            'height': '60px',
            'border-width': '2px',
            'border-color': '#ffffff'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#64748b',
            'target-arrow-color': '#64748b',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '10px',
            'text-background-color': '#ffffff',
            'text-background-opacity': 0.8,
            'text-background-padding': '2px'
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-color': '#ef4444',
            'border-width': '3px'
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#ef4444',
            'target-arrow-color': '#ef4444'
          }
        }
      ],
      layout: {
        name: 'dagre',
        // @ts-ignore
        rankDir: 'TB',
        nodeSep: 50,
        edgeSep: 50,
        rankSep: 100
      }
    });

    // 添加交互事件
    cyRef.current.on('tap', 'node', (evt) => {
      const node = evt.target;
      console.log('Node tapped:', node.data());
    });

    cyRef.current.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      console.log('Edge tapped:', edge.data());
    });

    // 適應容器大小
    const resizeObserver = new ResizeObserver(() => {
      if (cyRef.current) {
        cyRef.current.resize();
        cyRef.current.fit();
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [filteredData, isExpanded]);

  // 控制函數
  const zoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  const zoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() / 1.2);
  const fit = () => cyRef.current?.fit();
  const center = () => cyRef.current?.center();

  // 當組件展開時自動加載數據
  useEffect(() => {
    if (isExpanded && !graphData) {
      fetchGraphData();
    }
  }, [isExpanded, graphData]);

  const nodeTypeOptions = [
    { value: 'all', label: '全部節點' },
    { value: 'entity', label: '實體' },
    { value: 'event', label: '事件' },
    { value: 'chunk', label: '文本片段' },
    { value: 'visual_fact', label: '視覺事實' }
  ];

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Eye className="w-5 h-5" />
            知識圖譜視覺化
            <Badge variant="outline" className="ml-2">
              {filteredData?.nodes.length || 0} 節點, {filteredData?.edges.length || 0} 關係
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
                <EyeOff className="w-4 h-4" />
                收起
              </>
            ) : (
              <>
                <Eye className="w-4 h-4" />
                展開
              </>
            )}
          </Button>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent>
          {/* 控制面板 */}
          <div className="flex flex-wrap gap-4 mb-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
            {/* 搜索 */}
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4" />
              <Input
                placeholder="搜索節點..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-48"
              />
            </div>

            {/* 類型過濾 */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4" />
              <Select value={nodeTypeFilter} onValueChange={setNodeTypeFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {nodeTypeOptions.map(option => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 圖譜控制 */}
            <div className="flex items-center gap-1 ml-auto">
              <Button variant="outline" size="sm" onClick={zoomIn}>
                <ZoomIn className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={zoomOut}>
                <ZoomOut className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={fit}>
                <RotateCcw className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={() => fetchGraphData()}>
                刷新
              </Button>
            </div>
          </div>

          {/* 圖譜容器 */}
          <div className="relative border rounded-lg overflow-hidden" style={{ height: '600px' }}>
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-slate-900/80 z-10">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-6 h-6 animate-spin" />
                  <span>加載知識圖譜...</span>
                </div>
              </div>
            )}

            <div
              ref={containerRef}
              className="w-full h-full"
              style={{ display: loading ? 'none' : 'block' }}
            />
          </div>

          {/* 圖例 */}
          <div className="mt-4 flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span>實體</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span>事件</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-amber-500 rounded"></div>
              <span>文本片段</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4-4 bg-violet-500 rounded"></div>
              <span>視覺事實</span>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

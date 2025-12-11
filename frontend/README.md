# GraphRAG Frontend

React + Next.js 前端應用，用於GraphRAG智慧問答系統的用戶界面。

## 🚀 快速開始

### 安裝依賴
```bash
npm install
```

### 環境變數
複製並配置環境變數：
```bash
cp .env.local.example .env.local
```

編輯 `.env.local`:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_TIMEOUT=30000
```

### 啟動開發服務器
```bash
npm run dev
```

訪問 http://localhost:3000 查看應用。

## 🏗️ 技術架構

### 核心技術棧
- **Next.js 14+**: React全棧框架
- **React 18+**: 現代React特性
- **TypeScript**: 類型安全
- **Tailwind CSS**: 實用優先的CSS框架
- **shadcn/ui**: 現代UI組件庫

### 狀態管理
- **TanStack Query**: 服務端狀態管理
- **React Query DevTools**: 開發調試工具

### API集成
- **Axios**: HTTP客戶端
- **自動類型生成**: 基於FastAPI schema
- **錯誤處理**: 統一的錯誤處理機制

## 📁 專案結構

```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # 根佈局
│   ├── page.tsx           # 首頁
│   └── globals.css        # 全域樣式
├── components/            # React組件
│   ├── ui/               # shadcn/ui 組件
│   ├── QueryInterface.tsx # 查詢介面主組件
│   └── providers.tsx     # React Query Provider
├── services/             # API服務層
│   └── api.ts           # API客戶端
├── types/               # TypeScript類型定義
│   └── api.ts          # API相關類型
├── lib/                # 工具函數
│   └── utils.ts       # shadcn/ui 工具函數
└── hooks/              # 自定義React Hooks (準備中)
```

## 🎯 主要功能

### 智慧問答介面
- 多語言輸入支持 (中英文)
- 實時查詢建議和歷史記錄
- Agentic RAG智能查詢處理
- 查詢類型自動識別 (factual, analytical, visual, temporal, complex)
- 完整結果展示包含證據追溯
- 澄清問題智能提示

### 文件上傳系統
- 拖拽上傳和點擊選擇
- 支持多種格式 (PDF, DOCX, JPG, PNG)
- 批量上傳處理
- 實時上傳進度追蹤
- 文件驗證和錯誤處理
- 上傳狀態管理和移除功能

### Agentic RAG集成
- 完整的7個專業Agent支持
- 實時查詢處理和推理
- 證據溯源和可追溯性
- 信心度評估和結果驗證
- 錯誤恢復和用戶反饋

### 響應式設計
- 現代化的UI設計系統
- 深色模式支持
- 桌面、平板、手機全響應
- 無障礙訪問支持

## 🔧 開發指南

### 添加新組件
```bash
# 使用shadcn/ui添加組件
npx shadcn@latest add [component-name]

# 例如：添加對話框
npx shadcn@latest add dialog
```

### API類型更新
當後端API變更時：
1. 更新 `src/types/api.ts` 中的類型定義
2. 檢查 `src/services/api.ts` 中的實現
3. 確保組件中的使用是類型安全的

### 樣式指南
- 使用Tailwind CSS類
- 遵循shadcn/ui設計系統
- 支持深色模式
- 確保可訪問性

## 🚀 部署

### 生產構建
```bash
npm run build
npm run start
```

### 環境變數 (生產)
```env
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
NEXT_PUBLIC_API_TIMEOUT=30000
```

## 🧪 測試

### 運行測試 (準備中)
```bash
npm run test
```

### E2E測試 (準備中)
```bash
npm run test:e2e
```

## 📚 相關文檔

- [Next.js 文檔](https://nextjs.org/docs)
- [React 文檔](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [shadcn/ui](https://ui.shadcn.com)
- [TanStack Query](https://tanstack.com/query)

## 🤝 貢獻

1. Fork 此專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📄 授權

此專案採用 MIT 授權條款。

# Supabase Vector Database Setup

此目錄包含 Supabase pgvector 設置腳本，用於 GraphRAG 系統的向量存儲。

## 檔案說明

### supabase-setup.sql
完整的向量表初始化腳本，包含：
- 表結構創建
- 索引設置
- RLS (Row Level Security) 權限設置
- 測試查詢

### supabase-rls-fix.sql
專門用於修復向量表權限問題的腳本。

## ⚠️ 重要注意事項：向量維度設定

### 當前向量維度為 384
在 `supabase-setup.sql` 中，向量表的 `embedding` 欄位定義為：
```sql
embedding vector(384)
```

### 與環境變數的關係
`.env` 檔案中的 `EMBEDDING_DIMENSION=384` **不會自動更新** 向量表的結構！

- **SQL 腳本**: 靜態定義表結構，包括向量維度
- **環境變數**: 用於代碼邏輯和後備值驗證，不是動態表結構

### 何時需要修改向量維度？

當您需要完全替換嵌入模型時：
1. **修改 SQL 腳本**: 編輯 `supabase-setup.sql` 中的 `vector(新維度)`
2. **重建表**: 在 Supabase 中執行重建腳本（會刪除現有資料）
3. **更新 .env**: 修改 `EMBEDDING_DIMENSION` 為新維度值
4. **重新索引**: 重新執行文檔處理以生成新的向量

### 常見向量維度對應
```plaintext
- Sentence Transformers (all-MiniLM-L6-v2): 384
- OpenAI (text-embedding-ada-002): 1536
- Cohere: 1024
```

## 使用步驟

1. 在 Supabase SQL Editor 中執行 `supabase-setup.sql`
2. 如遇權限錯誤，執行 `supabase-rls-fix.sql`
3. 確認向量表已創建並可讀寫

## 排查問題

- **語法錯誤**: 確保使用 PostgreSQL 語法（非 MySQL）
- **權限問題**: 在開發環境使用 `supabase-rls-fix.sql` 設定寬鬆權限
- **向量維度問題**: 使用與嵌入模型匹配的維度

---

### 💡 開發建議
建議保留一個 `supabase-setup-dynamic.sql` 腳本模板，方便動態生成不同維度的表定義。

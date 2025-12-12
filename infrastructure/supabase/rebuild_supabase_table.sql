-- 重建Supabase vectors表為JSONB格式

-- 1. 刪除舊表
DROP TABLE IF EXISTS public.vectors;

-- 2. 啟用 pgvector 擴展
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. 創建新表使用JSONB
CREATE TABLE public.vectors (
    vector_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    embedding JSONB,  -- 使用JSONB存儲向量數組
    document_id UUID,
    chunk_id UUID,
    fact_id UUID,
    type TEXT check (type in ('chunk', 'vlm_region')),
    page INTEGER DEFAULT 1,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. 創建索引
CREATE INDEX idx_vectors_document_id ON public.vectors(document_id);
CREATE INDEX idx_vectors_chunk_id ON public.vectors(chunk_id);
CREATE INDEX idx_vectors_type ON public.vectors(type);

-- 5. 啟用RLS
ALTER TABLE public.vectors ENABLE ROW LEVEL SECURITY;

-- 6. 創建政策
CREATE POLICY "vectors_allow_all" ON public.vectors
FOR ALL USING (true) WITH CHECK (true);

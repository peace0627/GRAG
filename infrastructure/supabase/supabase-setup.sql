-- 完整的Supabase vectors表權限修復
-- 請按順序執行所有SQL語句

-- ⚠️ 注意：向量維度 384 是硬編碼的，與 .env 中的 EMBEDDING_DIMENSION 設定無關！
-- 如果需要修改向量維度，請直接更改下方的 vector(384) 並重建表

-- 1. 創建vectors表 (如果不存在)
CREATE TABLE IF NOT EXISTS public.vectors (
    vector_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    embedding vector(384),  -- ⚠️ 硬編碼向量維度，與 .env EMBEDDING_DIMENSION 無關
    document_id UUID,
    chunk_id UUID,
    fact_id UUID,
    type TEXT check (type in ('chunk', 'vlm_region')),
    page INTEGER DEFAULT 1,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 創建索引 (如果不存在)
CREATE INDEX IF NOT EXISTS idx_vectors_document_id ON public.vectors(document_id);
CREATE INDEX IF NOT EXISTS idx_vectors_chunk_id ON public.vectors(chunk_id);
CREATE INDEX IF NOT EXISTS idx_vectors_type ON public.vectors(type);

-- 3. 確保RLS已啟用
ALTER TABLE public.vectors ENABLE ROW LEVEL SECURITY;

-- 4. 刪除舊的衝突政策 (如果存在)
DROP POLICY IF EXISTS "Allow anon all operations on vectors" ON public.vectors;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON public.vectors;

-- 5. 創建新政策 - 允許所有操作 (開發環境)
CREATE POLICY "vectors_allow_all" ON public.vectors
FOR ALL USING (true) WITH CHECK (true);

-- 或者如果要更限制的政策，使用這個：
-- CREATE POLICY "vectors_allow_anon" ON public.vectors
-- FOR ALL USING (auth.role() = 'anon' OR auth.role() = 'authenticated');

-- 6. 檢查政策是否正確創建
SELECT schemaname, tablename, policyname,
       permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE tablename = 'vectors';

-- 7. 測試插入權限 (這個應該允許)
-- SELECT * FROM public.vectors LIMIT 1;

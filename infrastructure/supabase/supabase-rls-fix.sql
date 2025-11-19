-- 修復Supabase vectors表的RLS權限問題
-- 在Supabase SQL Editor中執行此脚本

-- 刪除可能存在的舊政策
DROP POLICY IF EXISTS "Allow anon all operations on vectors" ON public.vectors;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON public.vectors;

-- 允許anon用戶對vectors表進行所有操作 (開發環境)
CREATE POLICY "Allow anon all operations on vectors"
ON public.vectors
FOR ALL
USING (true)
WITH CHECK (true);

-- 如果你想更安全，可以用這個政策：
-- DROP POLICY IF EXISTS "Allow service role operations on vectors" ON public.vectors;
-- CREATE POLICY "Allow service role operations on vectors"
-- ON public.vectors
-- FOR ALL
-- USING (auth.role() = 'service_role')
-- WITH CHECK (auth.role() = 'service_role');

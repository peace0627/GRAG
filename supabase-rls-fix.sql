-- 修復Supabase vectors表的RLS權限問題
-- 在Supabase SQL Editor中執行此脚本

-- 允許anon用戶對vectors表進行所有操作 (開發環境)
CREATE POLICY IF NOT EXISTS "Allow anon all operations on vectors"
ON public.vectors
FOR ALL
USING (true)
WITH CHECK (true);

-- 如果你想更安全，可以用這個政策：
-- CREATE POLICY IF NOT EXISTS "Allow service role operations on vectors"
-- ON public.vectors
-- FOR ALL
-- USING (auth.role() = 'service_role')
-- WITH CHECK (auth.role() = 'service_role');

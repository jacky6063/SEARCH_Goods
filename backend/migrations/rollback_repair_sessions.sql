-- ============================================
-- repair_sessions 表回滾 Migration
-- 用途: 移除 repair_sessions 表及相關物件
-- 建立日期: 2025-11-25
-- ============================================

BEGIN;

-- 移除觸發器
DROP TRIGGER IF EXISTS trigger_repair_sessions_updated_at ON repair_sessions;

-- 移除觸發器函數
DROP FUNCTION IF EXISTS update_repair_sessions_updated_at();

-- 移除表 (CASCADE 會自動移除相關索引和約束)
DROP TABLE IF EXISTS repair_sessions CASCADE;

COMMIT;

-- ============================================
-- 回滾完成
-- ============================================
-- 
-- 驗證結果:
-- \dt repair_sessions (應該顯示不存在)
-- ============================================

-- ============================================
-- repair_sessions 表建立 Migration
-- 用途: 住宅維修對話會話管理與真人客服接手追蹤
-- 建立日期: 2025-11-25
-- ============================================

BEGIN;

-- 建立 repair_sessions 表
CREATE TABLE IF NOT EXISTS repair_sessions (
    -- 主鍵：會話唯一識別碼
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 對話模式控制
    manual_mode BOOLEAN DEFAULT false NOT NULL,
    
    -- 客服人員資訊
    operator_id VARCHAR(50),
    operator_name VARCHAR(100),
    operator_avatar TEXT,
    
    -- 會話狀態
    status VARCHAR(20) DEFAULT 'ongoing' NOT NULL,
    
    -- 時間戳記
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    mode_updated_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 擴充欄位
    metadata JSONB,
    
    -- 建立與更新時間
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 建立索引以優化查詢效能
CREATE INDEX IF NOT EXISTS idx_repair_sessions_status 
    ON repair_sessions(status);

CREATE INDEX IF NOT EXISTS idx_repair_sessions_manual_mode 
    ON repair_sessions(manual_mode);

CREATE INDEX IF NOT EXISTS idx_repair_sessions_started_at 
    ON repair_sessions(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_repair_sessions_operator_id 
    ON repair_sessions(operator_id) 
    WHERE operator_id IS NOT NULL;

-- 建立自動更新 updated_at 的觸發器函數
CREATE OR REPLACE FUNCTION update_repair_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 建立觸發器
DROP TRIGGER IF EXISTS trigger_repair_sessions_updated_at ON repair_sessions;
CREATE TRIGGER trigger_repair_sessions_updated_at
    BEFORE UPDATE ON repair_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_repair_sessions_updated_at();

-- 新增狀態值約束
ALTER TABLE repair_sessions
    DROP CONSTRAINT IF EXISTS check_status_values;

ALTER TABLE repair_sessions
    ADD CONSTRAINT check_status_values 
    CHECK (status IN ('ongoing', 'completed', 'expired', 'cancelled'));

-- 新增表和欄位註解
COMMENT ON TABLE repair_sessions IS '住宅維修對話會話管理表';
COMMENT ON COLUMN repair_sessions.session_id IS '會話唯一識別碼 (UUID)';
COMMENT ON COLUMN repair_sessions.manual_mode IS 'false=AI自動回覆, true=真人客服接手';
COMMENT ON COLUMN repair_sessions.operator_id IS '客服人員ID，接手時必填';
COMMENT ON COLUMN repair_sessions.operator_name IS '客服人員姓名，用於前端顯示';
COMMENT ON COLUMN repair_sessions.operator_avatar IS '客服人員頭像 URL';
COMMENT ON COLUMN repair_sessions.status IS '會話狀態: ongoing/completed/expired/cancelled';
COMMENT ON COLUMN repair_sessions.started_at IS '會話開始時間';
COMMENT ON COLUMN repair_sessions.mode_updated_at IS '最後一次切換 manual_mode 的時間';
COMMENT ON COLUMN repair_sessions.completed_at IS '會話結束時間';
COMMENT ON COLUMN repair_sessions.metadata IS '擴充 JSON 資料 (如客戶資訊、標籤等)';

COMMIT;

-- ============================================
-- Migration 完成
-- ============================================
-- 
-- 驗證執行結果:
-- SELECT * FROM repair_sessions LIMIT 1;
-- \d repair_sessions
--
-- 回滾此 Migration:
-- 執行 rollback_repair_sessions.sql
-- ============================================

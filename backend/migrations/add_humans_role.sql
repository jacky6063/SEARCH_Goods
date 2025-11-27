-- 將 message_role enum 加入 'Humans' 值
-- 執行日期: 2024-11-25
-- 目的: 支援客服人員回覆的獨立 role 類型，便於後續數據分析

-- 檢查當前 enum 定義
-- SELECT enum_range(NULL::message_role);

-- 新增 'Humans' 到 message_role enum
ALTER TYPE message_role ADD VALUE IF NOT EXISTS 'Humans';

-- 驗證新增成功
-- SELECT enum_range(NULL::message_role);
-- 預期輸出: {user,llm,Humans}

-- 注意事項:
-- 1. 此操作不會影響現有資料（user, llm 記錄保持不變）
-- 2. 新增後無法刪除 enum 值（PostgreSQL 限制）
-- 3. 執行前請確認已備份資料庫

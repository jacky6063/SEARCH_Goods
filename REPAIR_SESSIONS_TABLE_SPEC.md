# repair_sessions 表格設計規範

**建立日期：** 2025年11月25日  
**專案：** SEARCH_Goods - 住宅維修客服系統  
**用途：** 對話會話管理與真人客服接手追蹤

---

## 📊 表格用途

`repair_sessions` 是**住宅維修對話管理表**，用於追蹤和管理每個維修諮詢會話的狀態和元資料。

### 核心功能

1. **對話狀態管理** - 標記對話是 AI 自動回覆還是真人客服接手
2. **客服人員追蹤** - 記錄接手的客服人員資訊
3. **會話生命週期** - 追蹤對話從開始到結束的完整狀態
4. **彈窗通知基礎** - 前端檢測 `manual_mode` 變化時觸發真人客服彈窗

---

## 🗄️ 表結構定義

### SQL Schema

```sql
CREATE TABLE IF NOT EXISTS repair_sessions (
    -- 主鍵：會話唯一識別碼
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 對話模式控制
    manual_mode BOOLEAN DEFAULT false,  -- false=AI自動, true=真人接手
    
    -- 客服人員資訊
    operator_id VARCHAR(50),            -- 客服人員 ID
    operator_name VARCHAR(100),         -- 客服人員姓名
    operator_avatar TEXT,               -- 客服人員頭像 URL (可選)
    
    -- 會話狀態
    status VARCHAR(20) DEFAULT 'ongoing',  -- ongoing/completed/expired/cancelled
    
    -- 時間戳記
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- 會話開始時間
    mode_updated_at TIMESTAMP WITH TIME ZONE,           -- 最後一次切換模式時間
    completed_at TIMESTAMP WITH TIME ZONE,              -- 會話結束時間
    
    -- 擴充欄位
    metadata JSONB,                     -- 額外的 JSON 資料 (如客戶資訊、標籤等)
    
    -- 建立與更新時間
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引優化
CREATE INDEX idx_repair_sessions_status ON repair_sessions(status);
CREATE INDEX idx_repair_sessions_manual_mode ON repair_sessions(manual_mode);
CREATE INDEX idx_repair_sessions_started_at ON repair_sessions(started_at DESC);
CREATE INDEX idx_repair_sessions_operator_id ON repair_sessions(operator_id);
```

---

## 📋 欄位說明

| 欄位名稱 | 資料類型 | 必填 | 預設值 | 說明 |
|---------|---------|------|--------|------|
| `session_id` | UUID | ✅ | gen_random_uuid() | 會話唯一識別碼，主鍵 |
| `manual_mode` | BOOLEAN | ✅ | false | 對話模式：false=AI自動, true=真人接手 |
| `operator_id` | VARCHAR(50) | ❌ | NULL | 客服人員 ID，接手時必填 |
| `operator_name` | VARCHAR(100) | ❌ | NULL | 客服人員姓名，用於前端顯示 |
| `operator_avatar` | TEXT | ❌ | NULL | 客服人員頭像 URL |
| `status` | VARCHAR(20) | ✅ | 'ongoing' | 會話狀態 (ongoing/completed/expired/cancelled) |
| `started_at` | TIMESTAMP | ✅ | NOW() | 會話開始時間 |
| `mode_updated_at` | TIMESTAMP | ❌ | NULL | 最後一次切換 manual_mode 的時間 |
| `completed_at` | TIMESTAMP | ❌ | NULL | 會話結束時間 |
| `metadata` | JSONB | ❌ | NULL | 擴充 JSON 資料 |
| `created_at` | TIMESTAMP | ✅ | NOW() | 記錄建立時間 |
| `updated_at` | TIMESTAMP | ✅ | NOW() | 記錄更新時間 |

### 狀態值定義 (status)

- **`ongoing`**: 對話進行中（預設）
- **`completed`**: 對話已完成（客服結束對話或客戶滿意離開）
- **`expired`**: 對話已過期（超過閒置時間自動結束）
- **`cancelled`**: 對話已取消（客戶中斷或系統異常）

---

## 🔄 與其他表的關聯

### 與 `chat_messages` 表的關係

```
repair_sessions (會話元資料) 1 對多 chat_messages (對話內容)
    │
    └─ session_id (外鍵)
```

**分工:**
- **`repair_sessions`**: 記錄 **誰在服務、服務狀態、會話元資料**
- **`chat_messages`**: 記錄 **說了什麼、何時說的、誰說的**

### chat_messages 相關欄位

```sql
-- chat_messages 表中的關聯欄位
SELECT 
    message_id,
    session_id,          -- 關聯到 repair_sessions.session_id
    role,                -- 'user', 'llm', 'Humans'
    content,
    source_module,       -- 'repair' 表示維修模組
    created_at
FROM chat_messages
WHERE source_module = 'repair'
  AND session_id = 'abc-123-def';
```

---

## 💡 使用場景

### 場景 1: 建立新會話

```python
# 客戶發送第一則訊息時建立 session
from uuid import uuid4

session_id = str(uuid4())
supabase_client.table('repair_sessions').insert({
    'session_id': session_id,
    'manual_mode': False,  # 預設 AI 自動回覆
    'status': 'ongoing',
    'started_at': datetime.utcnow().isoformat()
}).execute()
```

### 場景 2: 客服人員接手對話

```python
# 客服點擊「接手」按鈕
supabase_client.table('repair_sessions').update({
    'manual_mode': True,
    'operator_id': 'OP001',
    'operator_name': '張小華',
    'operator_avatar': 'https://example.com/avatars/zhangxh.png',
    'mode_updated_at': datetime.utcnow().isoformat(),
    'updated_at': datetime.utcnow().isoformat()
}).eq('session_id', session_id).execute()
```

### 場景 3: 查詢待處理對話（客服後台）

```python
# 查詢所有 AI 正在處理的對話（可能需要客服接手）
result = supabase_client.table('repair_sessions')\
    .select('*')\
    .eq('manual_mode', False)\
    .eq('status', 'ongoing')\
    .order('started_at', desc=True)\
    .limit(50)\
    .execute()

ongoing_sessions = result.data
```

### 場景 4: 查詢客服工作負載

```python
# 統計每位客服人員正在處理的對話數
result = supabase_client.table('repair_sessions')\
    .select('operator_id, operator_name')\
    .eq('manual_mode', True)\
    .eq('status', 'ongoing')\
    .execute()

# 統計結果
from collections import Counter
workload = Counter(
    (s['operator_id'], s['operator_name']) 
    for s in result.data if s['operator_id']
)
```

### 場景 5: 前端檢測真人客服加入（觸發彈窗）

```javascript
// 前端輪詢檢查 manual_mode 狀態
async function checkManualModeStatus(sessionId) {
    const response = await fetch(
        `/api/repair/session/${sessionId}/status`
    );
    const data = await response.json();
    
    if (data.manual_mode && !isPopupShown) {
        // 觸發真人客服彈窗
        showOperatorPopup({
            operatorName: data.operator_name,
            operatorAvatar: data.operator_avatar
        });
        isPopupShown = true;
    }
}

// 每 3 秒輪詢一次
setInterval(() => checkManualModeStatus(currentSessionId), 3000);
```

### 場景 6: 結束對話

```python
# 客服或系統結束對話
supabase_client.table('repair_sessions').update({
    'status': 'completed',
    'completed_at': datetime.utcnow().isoformat(),
    'updated_at': datetime.utcnow().isoformat()
}).eq('session_id', session_id).execute()
```

---

## 🔌 API 端點規劃

### 1. 查詢會話狀態

```
GET /api/repair/session/{session_id}/status
```

**回應範例:**
```json
{
    "session_id": "abc-123-def",
    "manual_mode": true,
    "operator_id": "OP001",
    "operator_name": "張小華",
    "operator_avatar": "https://example.com/avatars/zhangxh.png",
    "status": "ongoing",
    "started_at": "2025-11-25T10:30:00Z",
    "mode_updated_at": "2025-11-25T10:35:00Z"
}
```

### 2. 切換對話模式

```
POST /api/repair/manual_mode
```

**請求 Body:**
```json
{
    "session_id": "abc-123-def",
    "manual_mode": true,
    "operator_id": "OP001",
    "operator_name": "張小華"
}
```

**回應:**
```json
{
    "success": true,
    "session_id": "abc-123-def",
    "manual_mode": true,
    "operator_id": "OP001",
    "message": "✅ 已切換為真人接手"
}
```

### 3. 查詢活躍對話列表

```
GET /api/repair/active_sessions?limit=50&status=ongoing
```

**回應範例:**
```json
{
    "sessions": [
        {
            "session_id": "abc-123",
            "manual_mode": false,
            "status": "ongoing",
            "last_message": "水龍頭一直滴水...",
            "last_message_at": "2025-11-25T10:30:00Z",
            "message_count": 3,
            "operator_name": null
        },
        {
            "session_id": "def-456",
            "manual_mode": true,
            "status": "ongoing",
            "last_message": "好的，請稍候...",
            "last_message_at": "2025-11-25T10:25:00Z",
            "message_count": 5,
            "operator_name": "張小華"
        }
    ],
    "total": 2
}
```

---

## 📊 數據分析查詢範例

### 統計真人介入率

```sql
SELECT 
    COUNT(*) FILTER (WHERE manual_mode = true) * 100.0 / COUNT(*) AS intervention_rate,
    COUNT(*) AS total_sessions,
    COUNT(*) FILTER (WHERE manual_mode = true) AS manual_sessions,
    COUNT(*) FILTER (WHERE manual_mode = false) AS ai_only_sessions
FROM repair_sessions
WHERE started_at >= NOW() - INTERVAL '7 days'
  AND status IN ('completed', 'ongoing');
```

### 客服人員績效統計

```sql
SELECT 
    operator_name,
    COUNT(*) AS handled_sessions,
    AVG(EXTRACT(EPOCH FROM (completed_at - mode_updated_at))/60) AS avg_handling_time_minutes
FROM repair_sessions
WHERE manual_mode = true
  AND status = 'completed'
  AND started_at >= NOW() - INTERVAL '30 days'
GROUP BY operator_name
ORDER BY handled_sessions DESC;
```

### 高峰時段分析

```sql
SELECT 
    EXTRACT(HOUR FROM started_at) AS hour,
    COUNT(*) AS session_count,
    COUNT(*) FILTER (WHERE manual_mode = true) AS manual_mode_count
FROM repair_sessions
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
```

---

## 🚀 實作檢查清單

### 資料庫層

- [ ] 在 Supabase 建立 `repair_sessions` 表
- [ ] 建立必要的索引 (status, manual_mode, started_at, operator_id)
- [ ] 設定 Row Level Security (RLS) 政策
- [ ] 建立觸發器自動更新 `updated_at` 欄位

### 後端 API

- [ ] 實作 `GET /api/repair/session/{session_id}/status`
- [ ] 完善 `POST /api/repair/manual_mode` 端點（目前有 TODO）
- [ ] 實作 `GET /api/repair/active_sessions`
- [ ] 實作 `POST /api/repair/session/{session_id}/complete`
- [ ] 在 `/api/repair/chat` 端點建立新 session 時插入記錄

### 前端

- [ ] 在 `index.html` 新增輪詢機制檢測 `manual_mode` 變化
- [ ] 實作真人客服彈窗 UI 組件
- [ ] 在 `repair_chat_viewer.html` 顯示活躍對話列表
- [ ] 實作「接手」按鈕功能並呼叫 API

### 測試

- [ ] 單元測試：表操作 CRUD
- [ ] 整合測試：API 端點功能
- [ ] E2E 測試：客服接手完整流程
- [ ] 壓力測試：高並發對話處理

---

## ⚠️ 注意事項

### 1. 資料一致性

- 確保 `chat_messages.session_id` 與 `repair_sessions.session_id` 一致
- 使用外鍵約束保證參照完整性（可選，視需求）

### 2. 效能考量

- 定期清理過期的 `completed` 或 `expired` 記錄（保留 90 天）
- 使用分區表（Partition）處理大量歷史資料

### 3. 安全性

- 使用 Supabase RLS 限制客服人員只能查看/修改自己負責的對話
- API 端點需要驗證 `operator_id` 權限

### 4. 擴展性

- `metadata` JSONB 欄位可儲存額外資訊：
  - 客戶滿意度評分
  - 問題分類標籤
  - 優先級
  - 來源渠道 (web/mobile/api)

---

## 📝 Migration Script

### 建立表格

```sql
-- 檔案: backend/migrations/create_repair_sessions.sql

BEGIN;

-- 建立 repair_sessions 表
CREATE TABLE IF NOT EXISTS repair_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manual_mode BOOLEAN DEFAULT false NOT NULL,
    operator_id VARCHAR(50),
    operator_name VARCHAR(100),
    operator_avatar TEXT,
    status VARCHAR(20) DEFAULT 'ongoing' NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    mode_updated_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 建立索引
CREATE INDEX idx_repair_sessions_status ON repair_sessions(status);
CREATE INDEX idx_repair_sessions_manual_mode ON repair_sessions(manual_mode);
CREATE INDEX idx_repair_sessions_started_at ON repair_sessions(started_at DESC);
CREATE INDEX idx_repair_sessions_operator_id ON repair_sessions(operator_id) WHERE operator_id IS NOT NULL;

-- 建立自動更新 updated_at 的觸發器
CREATE OR REPLACE FUNCTION update_repair_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_repair_sessions_updated_at
    BEFORE UPDATE ON repair_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_repair_sessions_updated_at();

-- 新增約束
ALTER TABLE repair_sessions
    ADD CONSTRAINT check_status_values 
    CHECK (status IN ('ongoing', 'completed', 'expired', 'cancelled'));

-- 新增註解
COMMENT ON TABLE repair_sessions IS '住宅維修對話會話管理表';
COMMENT ON COLUMN repair_sessions.manual_mode IS 'false=AI自動回覆, true=真人客服接手';
COMMENT ON COLUMN repair_sessions.operator_id IS '客服人員ID，接手時必填';
COMMENT ON COLUMN repair_sessions.status IS '會話狀態: ongoing/completed/expired/cancelled';

COMMIT;
```

### 回滾腳本

```sql
-- 檔案: backend/migrations/rollback_repair_sessions.sql

BEGIN;

DROP TRIGGER IF EXISTS trigger_repair_sessions_updated_at ON repair_sessions;
DROP FUNCTION IF EXISTS update_repair_sessions_updated_at();
DROP TABLE IF EXISTS repair_sessions;

COMMIT;
```

---

## 🔗 相關文件

- [客服人工回覆系統設計.md](./客服人工回覆系統設計.md) - 完整系統設計文件
- [UPGRADE_GUIDE.md](./backend/migrations/UPGRADE_GUIDE.md) - Humans role 升級指南
- [repair_chat_viewer.html](./frontend/repair_chat_viewer.html) - 客服後台介面

---

## 📅 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0 | 2025-11-25 | 初始版本，定義表結構與使用場景 |

---

**維護者:** SEARCH_Goods 開發團隊  
**最後更新:** 2025年11月25日

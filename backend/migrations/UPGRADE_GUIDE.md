# 住宅維修服務 - 資料庫 Role 欄位升級指南

## 📋 目標

將 `chat_messages.role` 欄位的 enum 類型加入 `'Humans'` 值，支援：
- `'user'` - 使用者訊息
- `'llm'` - AI 系統回覆
- `'Humans'` - **客服人員回覆**（新增）

## 🎯 優點

### 1. 資料分析更清晰
```sql
-- 統計客服回覆數量
SELECT COUNT(*) FROM chat_messages WHERE role = 'Humans';

-- 分析客服回覆時間分布
SELECT DATE_TRUNC('hour', created_at) as hour, COUNT(*) 
FROM chat_messages 
WHERE role = 'Humans'
GROUP BY hour
ORDER BY hour;

-- 客服平均回覆速度
SELECT 
  session_id,
  AVG(EXTRACT(EPOCH FROM (created_at - LAG(created_at) OVER (PARTITION BY session_id ORDER BY created_at)))) as avg_response_seconds
FROM chat_messages
WHERE role = 'Humans';
```

### 2. 不需要解析內容前綴
```python
# 之前：需要檢查內容前綴
if msg['content'].startswith('[OPERATOR:'):
    is_human = True

# 之後：直接檢查 role
if msg['role'] == 'Humans':
    is_human = True
```

### 3. 資料庫層級過濾
```sql
-- 查詢只有客服參與的會話
SELECT DISTINCT session_id 
FROM chat_messages 
WHERE role = 'Humans';

-- 查詢純 AI 會話（無客服介入）
SELECT session_id 
FROM chat_messages 
GROUP BY session_id 
HAVING SUM(CASE WHEN role = 'Humans' THEN 1 ELSE 0 END) = 0;
```

---

## 🔧 升級步驟

### Step 1: 更新 .env 檔案（如果尚未設定）

編輯 `backend/.env`，加入 Supabase 連線資訊：

```bash
# ========== 🗄️ Supabase 資料庫設定 ==========
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key  # 選填，用於管理操作
```

### Step 2: 執行資料庫 Migration

**方法 A - Supabase Dashboard（推薦）**

1. 登入 Supabase Dashboard
2. 前往 SQL Editor: `https://your-project.supabase.co/project/_/sql`
3. 執行以下 SQL：

```sql
-- 新增 'Humans' 到 message_role enum
ALTER TYPE message_role ADD VALUE IF NOT EXISTS 'Humans';

-- 驗證新增成功
SELECT enum_range(NULL::message_role);
-- 預期輸出: {user,llm,Humans}
```

**方法 B - psql 命令列**

```bash
cd backend/migrations
psql <YOUR_DATABASE_URL> -f add_humans_role.sql
```

**方法 C - Supabase CLI**

```bash
supabase db execute --file backend/migrations/add_humans_role.sql
```

### Step 3: 更新後端程式碼

編輯 `backend/app.py`，Line ~2213：

**修改前：**
```python
insert_result = supabase_client.table('chat_messages').insert({
    'session_id': session_id,
    'role': 'llm',  # ❌ 使用 llm 因為 Humans 不被支援
    'content': content_with_marker,
    # ...
}).execute()
```

**修改後：**
```python
insert_result = supabase_client.table('chat_messages').insert({
    'session_id': session_id,
    'role': 'Humans',  # ✅ 直接使用 Humans role
    'content': reply_content,  # ✅ 不需要加前綴
    # ...
}).execute()
```

### Step 4: 更新前端程式碼（簡化）

編輯 `frontend/repair_chat_viewer.html`：

**修改前（Lines 1093-1112）：**
```javascript
// 檢測真人客服回覆（三種標記）
const isOperatorReply = msg.content && (
    msg.content.startsWith('[OPERATOR:') ||
    msg.content.startsWith('[HUMAN_REPLY]') ||
    msg.content.startsWith('[客服')
);

// 提取客服名稱（優先 [OPERATOR:name]）
let operatorName = '客服人員';
if (msg.content.startsWith('[OPERATOR:')) {
    const match = msg.content.match(/^\[OPERATOR:([^\]]+)\]/);
    if (match) operatorName = match[1];
} else if (msg.content.startsWith('[客服')) {
    const match = msg.content.match(/^\[客服\s+([^\]]+)\]/);
    if (match) operatorName = match[1];
}

const displayRole = msg.role === 'user' ? 'user' : (isOperatorReply ? 'Humans' : 'llm');
```

**修改後（簡化）：**
```javascript
// 直接檢查 role 欄位
const displayRole = msg.role;  // 'user', 'llm', 或 'Humans'

// 提取客服名稱（從額外欄位或預設）
const operatorName = msg.operator_name || '客服人員';
```

### Step 5: 測試驗證

```bash
# 1. 發送客服回覆
curl -X POST "http://localhost:8000/api/repair/session/{session_id}/reply" \
  -F "reply=您好，我是客服小美，馬上為您處理。" \
  -F "operator_name=小美"

# 2. 查詢訊息，檢查 role
curl "http://localhost:8000/api/repair/session/{session_id}/messages" | jq '.messages[] | {role, content}'

# 預期看到:
# {
#   "role": "Humans",
#   "content": "您好，我是客服小美，馬上為您處理。"
# }
```

### Step 6: 資料遷移（選填）

如果要將舊資料（使用 `[OPERATOR:]` 前綴）轉換為新格式：

```sql
-- 更新舊資料的 role 為 Humans
UPDATE chat_messages
SET 
  role = 'Humans',
  content = REGEXP_REPLACE(content, '^\[OPERATOR:[^\]]+\]\s*', ''),
  updated_at = NOW()
WHERE 
  role = 'llm' 
  AND content ~ '^\[OPERATOR:';

-- 更新其他舊格式
UPDATE chat_messages
SET 
  role = 'Humans',
  content = REGEXP_REPLACE(content, '^\[HUMAN_REPLY\]\s*', ''),
  updated_at = NOW()
WHERE 
  role = 'llm' 
  AND content ~ '^\[HUMAN_REPLY\]';

UPDATE chat_messages
SET 
  role = 'Humans',
  content = REGEXP_REPLACE(content, '^\[客服\s+[^\]]+\]\s*', ''),
  updated_at = NOW()
WHERE 
  role = 'llm' 
  AND content ~ '^\[客服';
```

---

## 📊 升級後效果

### 資料庫層級
| 欄位 | 舊值 | 新值 |
|------|------|------|
| role | `'llm'` | `'Humans'` |
| content | `'[OPERATOR:小美]您好...'` | `'您好...'`（無前綴） |

### 前端顯示
- 無需檢查內容前綴
- 直接根據 `msg.role === 'Humans'` 判斷
- 程式碼更簡潔，效能更好

### 資料分析
```sql
-- 客服工作量統計
SELECT 
  DATE(created_at) as date,
  COUNT(*) as replies,
  COUNT(DISTINCT session_id) as sessions
FROM chat_messages
WHERE role = 'Humans'
GROUP BY date
ORDER BY date DESC;

-- 客服回覆率
SELECT 
  COUNT(DISTINCT CASE WHEN role = 'Humans' THEN session_id END) * 100.0 / 
  COUNT(DISTINCT session_id) as human_reply_rate
FROM chat_messages;
```

---

## ⚠️ 注意事項

1. **不可逆操作**：PostgreSQL enum 值新增後無法刪除
2. **向下相容**：舊的前端程式碼依然能運作（role 為 Humans 時會顯示）
3. **備份建議**：執行前建議備份資料庫
4. **分階段部署**：
   - 先執行 SQL migration
   - 再部署後端程式碼
   - 最後更新前端程式碼

---

## 🚀 快速執行清單

- [ ] 設定 Supabase 環境變數（`.env`）
- [ ] 執行 SQL migration（新增 Humans enum 值）
- [ ] 驗證 enum 更新成功
- [ ] 修改後端 `app.py`（使用 `role='Humans'`）
- [ ] 修改前端判斷邏輯（簡化為直接檢查 role）
- [ ] 測試新訊息寫入
- [ ] 測試前端顯示
- [ ] （選填）遷移舊資料

---

**建議開發順序：**
1. 今天：執行資料庫 migration + 修改後端
2. 測試：確認新資料正確寫入 `role='Humans'`
3. 明天：修改前端 + 清理舊的前綴檢測邏輯
4. 未來：遷移歷史資料（可選）

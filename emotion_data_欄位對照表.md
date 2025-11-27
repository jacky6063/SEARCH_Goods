# emotion_data 欄位中英文對照表

## 📊 資料庫欄位結構

### PostgreSQL 欄位定義
```sql
ALTER TABLE chat_messages 
ADD COLUMN emotion_data JSONB DEFAULT NULL;
```

---

## 🔤 JSON 欄位對照表

### 頂層欄位 (Top-level Fields)

| 中文名稱 | 英文欄位名 | 資料型態 | 值範圍 | 說明 |
|---------|-----------|---------|--------|------|
| 不安程度 | `anxiety_level` | Integer | 0-10 | 焦慮、擔心、害怕的程度 |
| 急迫感 | `urgency_level` | Integer | 0-10 | 緊急、需立即處理的程度 |
| 生氣指數 | `anger_level` | Integer | 0-10 | 憤怒、不滿、抱怨的程度 |
| 關鍵字列表 | `keywords` | Array[String] | - | 觸發情緒判讀的關鍵字 |
| 判斷理由 | `reasoning` | String | - | LLM 分析的理由說明 |
| 分析時間 | `analyzed_at` | ISO8601 | - | 情緒分析執行的時間戳 |
| 觸發閾值 | `trigger_threshold` | Object | - | 記錄當時使用的閾值設定 |

### 觸發閾值子物件 (trigger_threshold)

| 中文名稱 | 英文欄位名 | 資料型態 | 值範圍 | 說明 |
|---------|-----------|---------|--------|------|
| 不安閾值 | `anxiety` | Integer | 0-10 | 達到此值才記錄不安情緒 |
| 急迫閾值 | `urgency` | Integer | 0-10 | 達到此值才記錄急迫情緒 |
| 生氣閾值 | `anger` | Integer | 0-10 | 達到此值才記錄生氣情緒 |

---

## 📋 完整範例

### JSON 資料範例
```json
{
  "anxiety_level": 8,
  "urgency_level": 9,
  "anger_level": 3,
  "keywords": ["瓦斯", "洩漏", "危險", "趕快"],
  "reasoning": "訊息包含緊急危險關鍵字（瓦斯洩漏），使用多個驚嘆號，語氣急促，顯示高度焦慮和急迫性",
  "analyzed_at": "2025-11-27T10:30:15.123Z",
  "trigger_threshold": {
    "anxiety": 7,
    "urgency": 8,
    "anger": 6
  }
}
```

### SQL 查詢範例
```sql
-- 查詢高急迫性訊息
SELECT 
    message_id,
    content,
    emotion_data->>'urgency_level' as 急迫程度,
    emotion_data->>'reasoning' as 分析理由,
    created_at
FROM chat_messages
WHERE emotion_data IS NOT NULL
  AND (emotion_data->>'urgency_level')::int >= 8
ORDER BY created_at DESC;

-- 查詢包含特定關鍵字的情緒訊息
SELECT 
    message_id,
    content,
    emotion_data->'keywords' as 關鍵字,
    emotion_data->>'anxiety_level' as 不安程度
FROM chat_messages
WHERE emotion_data ? 'keywords'
  AND emotion_data->'keywords' @> '["瓦斯"]'::jsonb;

-- 統計各情緒等級的訊息數量
SELECT 
    CASE 
        WHEN (emotion_data->>'anxiety_level')::int >= 8 THEN '高度不安'
        WHEN (emotion_data->>'anxiety_level')::int >= 5 THEN '中度不安'
        ELSE '低度不安'
    END as 不安等級,
    COUNT(*) as 訊息數量
FROM chat_messages
WHERE emotion_data IS NOT NULL
GROUP BY 不安等級;
```

---

## 🔧 前端顯示對照

### 情緒等級文字對照

| 分數範圍 | 中文顯示 | 英文 | CSS Class | 顏色 |
|---------|---------|------|-----------|------|
| 8-10 | 高度不安 | High Anxiety | `emotion-high` | 紅色 #ef4444 |
| 5-7 | 中度不安 | Medium Anxiety | `emotion-medium` | 橙色 #f59e0b |
| 1-4 | 低度不安 | Low Anxiety | `emotion-low` | 黃色 #fbbf24 |
| 0 | 無 | None | - | - |

### Emoji 對照表

| 情緒類型 | Emoji | 中文 | 英文 |
|---------|-------|------|------|
| 不安程度 | 😰 | 焦慮 | Anxiety |
| 急迫感 | ⚡ | 緊急 | Urgency |
| 生氣指數 | 😠 | 憤怒 | Anger |

---

## 🎨 前端 HTML 範例

```html
<!-- 情緒標籤顯示 -->
<div class="emotion-badges">
    <span class="badge emotion-high">
        😰 不安 8/10
    </span>
    <span class="badge emotion-high">
        ⚡ 急迫 9/10
    </span>
    <span class="badge emotion-low">
        😠 生氣 3/10
    </span>
</div>
```

### JavaScript 渲染函數
```javascript
function renderEmotionBadges(emotionData) {
    if (!emotionData) return '';
    
    const badges = [];
    
    // 不安程度
    if (emotionData.anxiety_level >= 5) {
        const level = getEmotionLevel(emotionData.anxiety_level);
        badges.push(`
            <span class="badge emotion-${level}">
                😰 不安 ${emotionData.anxiety_level}/10
            </span>
        `);
    }
    
    // 急迫感
    if (emotionData.urgency_level >= 5) {
        const level = getEmotionLevel(emotionData.urgency_level);
        badges.push(`
            <span class="badge emotion-${level}">
                ⚡ 急迫 ${emotionData.urgency_level}/10
            </span>
        `);
    }
    
    // 生氣指數
    if (emotionData.anger_level >= 5) {
        const level = getEmotionLevel(emotionData.anger_level);
        badges.push(`
            <span class="badge emotion-${level}">
                😠 生氣 ${emotionData.anger_level}/10
            </span>
        `);
    }
    
    return badges.join('');
}

function getEmotionLevel(score) {
    if (score >= 8) return 'high';
    if (score >= 5) return 'medium';
    return 'low';
}
```

---

## 📊 統計分析欄位

### 前端統計卡片對照

| 統計項目 | 中文名稱 | 英文 Key | 計算方式 |
|---------|---------|----------|---------|
| 高度不安 | 高不安數 | `high_anxiety_count` | `anxiety_level >= 8` |
| 高度急迫 | 高急迫數 | `high_urgency_count` | `urgency_level >= 8` |
| 高度憤怒 | 高憤怒數 | `high_anger_count` | `anger_level >= 8` |
| 中度不安 | 中不安數 | `medium_anxiety_count` | `5 <= anxiety_level < 8` |
| 中度急迫 | 中急迫數 | `medium_urgency_count` | `5 <= urgency_level < 8` |
| 中度憤怒 | 中憤怒數 | `medium_anger_count` | `5 <= anger_level < 8` |
| 總情緒訊息數 | 情緒訊息總數 | `total_emotion_messages` | `emotion_data IS NOT NULL` |

---

## 🔄 API Response 對照

### GET /api/repair/chat_logs 回應格式

```json
{
  "date": "2025-11-27",
  "total_count": 156,
  "user_count": 78,
  "llm_count": 78,
  "session_count": 26,
  "emotion_stats": {
    "total_emotion_messages": 12,
    "high_anxiety_count": 3,
    "high_urgency_count": 5,
    "high_anger_count": 1,
    "medium_anxiety_count": 4,
    "medium_urgency_count": 2,
    "medium_anger_count": 2
  },
  "messages": [
    {
      "message_id": 1234,
      "session_id": "uuid-xxx",
      "role": "user",
      "content": "瓦斯好像在漏！！！很危險！",
      "created_at": "2025-11-27T10:30:00Z",
      "emotion_data": {
        "anxiety_level": 8,
        "urgency_level": 9,
        "anger_level": 3,
        "keywords": ["瓦斯", "漏", "危險"],
        "reasoning": "...",
        "analyzed_at": "2025-11-27T10:30:15Z"
      }
    }
  ]
}
```

---

## 📝 配置文件對照

### emotion_analysis_config.json

```json
{
  "version": "1.0.0",
  "updated_at": "2025-11-27T00:00:00Z",
  "thresholds": {
    "anxiety": 7,
    "urgency": 8,
    "anger": 6
  },
  "display_labels": {
    "zh-TW": {
      "anxiety": "不安程度",
      "urgency": "急迫感",
      "anger": "生氣指數",
      "high": "高度",
      "medium": "中度",
      "low": "低度"
    },
    "en": {
      "anxiety": "Anxiety Level",
      "urgency": "Urgency Level",
      "anger": "Anger Level",
      "high": "High",
      "medium": "Medium",
      "low": "Low"
    }
  }
}
```

---

## 🎯 快速參考

### 主要欄位速查表

```
emotion_data (JSONB)
├── anxiety_level (不安程度) : 0-10
├── urgency_level (急迫感) : 0-10
├── anger_level (生氣指數) : 0-10
├── keywords (關鍵字) : Array
├── reasoning (判斷理由) : String
├── analyzed_at (分析時間) : ISO8601
└── trigger_threshold (觸發閾值)
    ├── anxiety : 0-10
    ├── urgency : 0-10
    └── anger : 0-10
```

### 常用查詢條件

```sql
-- 查詢有情緒分析的訊息
WHERE emotion_data IS NOT NULL

-- 查詢高急迫性
WHERE (emotion_data->>'urgency_level')::int >= 8

-- 查詢包含特定關鍵字
WHERE emotion_data->'keywords' @> '["瓦斯"]'::jsonb

-- 查詢今天的情緒訊息
WHERE DATE(created_at) = CURRENT_DATE 
  AND emotion_data IS NOT NULL
```

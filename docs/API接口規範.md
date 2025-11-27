# API 接口規範

## 📋 概述

SEARCH_Goods 系統提供 RESTful API 接口，支援商品搜尋、智能聊天和建議推薦功能。

## 🌐 基礎資訊

### 基礎 URL
```
本地開發: http://localhost:8000
生產環境: https://your-domain.com
```

### 通用回應格式
```json
{
  "ok": true,
  "data": {},
  "message": "",
  "timestamp": "2025-10-29T10:30:00Z"
}
```

### 錯誤回應格式
```json
{
  "ok": false,
  "error": "錯誤類型",
  "message": "錯誤描述",
  "details": {},
  "timestamp": "2025-10-29T10:30:00Z"
}
```

## 🔍 商品搜尋 API

### POST /api/search
商品搜尋接口，支援自然語言查詢和結構化篩選。

#### 請求參數
```json
{
  "query": "燕麥粥",
  "limit": 10,
  "offset": 0,
  "filters": {
    "category": "食品",
    "price_min": 50,
    "price_max": 500,
    "has_special": true
  },
  "sort_by": "relevance"  // relevance | price_asc | price_desc
}
```

#### 回應範例
```json
{
  "ok": true,
  "results": [
    {
      "id": "4806533133019",
      "name": "冷壓純鮮椰子油/550ml",
      "price": "428",
      "special_offer": "",
      "category": "植物油",
      "brand": "瑞雀",
      "description": "椰子油含有豐富中鏈脂肪及月桂酸...",
      "image_url": "https://example.com/image.jpg",
      "shop_url": "https://example.com/shop/123",
      "stock": 13,
      "score": 4.2
    }
  ],
  "total": 1,
  "query": "燕麥粥",
  "filters_applied": {
    "category": "食品"
  },
  "search_time_ms": 150
}
```

## 💬 聊天對話 API

### POST /api/chat
智能聊天接口，支援上下文感知的商品諮詢。

#### 請求參數
```json
{
  "message": "椰子油對健康有什麼幫助？",
  "history": [
    {
      "role": "user",
      "content": "你好"
    },
    {
      "role": "assistant", 
      "content": "您好！我是智能客服，有什麼可以幫您的嗎？"
    }
  ],
  "session_id": "abc123",
  "topn": 8
}
```

#### 回應範例
```json
{
  "ok": true,
  "reply": "椰子油含有豐富的中鏈脂肪酸，對健康有以下幫助...",
  "intent": "information",
  "intent_subtype": "health",
  "suggestion_ids": ["4806533133019"],
  "action": {
    "type": "none"
  },
  "alignment": {
    "intent": "product_search",
    "items": [
      {
        "id": "4806533133019",
        "name": "冷壓純鮮椰子油/550ml"
      }
    ],
    "query": "椰子油"
  },
  "structured_payload": {
    "summary": "我找到 1 款商品，詳細如下：",
    "items": [
      {
        "index": 1,
        "商品編號": "4806533133019",
        "商品名稱": "冷壓純鮮椰子油/550ml",
        "商品描述": "椰子油有機安心，暖胃即享好滋味",
        "商品價格": "428",
        "商品特價": "",
        "購物連結": "https://example.com/shop/123",
        "商品圖片網址": "https://example.com/image.jpg"
      }
    ]
  },
  "session_id": "abc123",
  "context_info": {
    "action": "direct_search",
    "product": "椰子油",
    "confidence": 0.9
  }
}
```

## 🎯 建議推薦 API

### POST /api/suggest
基於會話ID獲取個性化商品建議。

#### 請求參數
```json
{
  "session_id": "abc123",
  "suggestion_type": "1",  // 1=原建議 | 2=特價關聯 | 3=智慧搭配
  "limit": 6
}
```

#### 回應範例
```json
{
  "ok": true,
  "suggestions": [
    {
      "id": "4806533133019",
      "name": "冷壓純鮮椰子油/550ml",
      "price": "428",
      "special_offer": "",
      "reason": "基於您的健康諮詢需求",
      "confidence": 0.95
    }
  ],
  "suggestion_type": "1",
  "total": 1,
  "session_info": {
    "created_at": "2025-10-29T10:25:00Z",
    "query_terms": ["椰子油", "健康"]
  }
}
```

## 🔧 管理 API

### POST /api/admin/clear-cache
清除系統快取（需要管理員權限）。

#### 請求標頭
```
Authorization: Bearer {ADMIN_TOKEN}
```

#### 回應範例
```json
{
  "ok": true,
  "message": "快取已清除",
  "cleared_items": {
    "product_cache": true,
    "session_cache": 15,
    "suggest_cache": 8
  }
}
```

### POST /api/admin/upload-csv
上傳商品資料檔案（需要管理員權限）。

#### 請求格式
```
Content-Type: multipart/form-data

file: CSV檔案
backup: true/false (是否備份現有檔案)
```

#### 回應範例
```json
{
  "ok": true,
  "message": "檔案上傳成功",
  "details": {
    "filename": "VIEW_GOODS_enhanced.csv",
    "size": 1024000,
    "products_count": 1250,
    "backup_created": true
  }
}
```

## 📊 系統狀態 API

### GET /health
系統健康檢查接口。

#### 回應範例
```json
{
  "ok": true,
  "status": "healthy",
  "timestamp": "2025-10-29T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "ok",
    "llm_service": "ok", 
    "cache": "ok"
  },
  "metrics": {
    "uptime_seconds": 86400,
    "active_sessions": 5,
    "total_products": 1250
  }
}
```

## ⚠️ 錯誤碼說明

| 錯誤碼 | 說明 | 處理建議 |
|--------|------|----------|
| 400 | 請求參數錯誤 | 檢查請求格式和必要參數 |
| 401 | 未授權訪問 | 提供有效的認證資訊 |
| 404 | 資源不存在 | 確認請求的資源路徑 |
| 429 | 請求頻率過高 | 降低請求頻率或稍後重試 |
| 500 | 伺服器內部錯誤 | 聯絡系統管理員 |
| 503 | 服務暫時不可用 | 系統維護中，請稍後重試 |

## 🔐 認證與權限

### API Key 認證
```bash
# 在請求標頭中添加 API Key
curl -H "X-API-Key: your-api-key" \
     -X POST \
     https://api.example.com/api/search
```

### 管理員權限
管理 API 需要在環境變數中設置 `ADMIN_TOKEN`：
```bash
export ADMIN_TOKEN=your-secure-admin-token
```

## 📝 請求範例

### 使用 curl
```bash
# 商品搜尋
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "燕麥", "limit": 5}'

# 聊天對話
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "推薦一些健康的油品",
    "history": []
  }'
```

### 使用 JavaScript
```javascript
// 商品搜尋
const searchProducts = async (query) => {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: query,
      limit: 10
    })
  });
  return await response.json();
};

// 聊天對話
const sendChatMessage = async (message, history) => {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      history: history || []
    })
  });
  return await response.json();
};
```

## 🎛️ 環境變數配置

### LLM 服務配置
```bash
# OpenAI API 配置
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# LLM 功能開關
USE_LLM_EXPAND=true
USE_LLM_SHORTDESC=true
USE_LLM_INTENT=true
USE_CHAT_MODE=true
```

### 系統配置
```bash
# 資料路徑
DATA_PATH=/path/to/VIEW_GOODS_enhanced.csv

# 管理權限
ADMIN_TOKEN=your-secure-admin-token
ALLOW_DEV_ADMIN=1

# 伺服器配置
HOST=0.0.0.0
PORT=8000
```

---

> **版本**: v1.0  
> **更新日期**: 2025年10月29日  
> **維護者**: SEARCH_Goods API 團隊
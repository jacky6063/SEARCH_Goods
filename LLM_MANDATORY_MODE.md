# 強制 LLM 互動模式修改方案

## 📋 修改目標

實現以下需求：
1. **一律經過 LLM 給使用者互動**
2. **互動中理解使用者的商品需求**  
3. **有商品需求時找尋 VIEW_GOODS_enhanced.csv 是否有適合的商品**
4. **如果都沒有，禮貌性回覆使用者**
5. **有走現有的商品模式**

## 🔧 主要修改內容

### 1. LLM 配置強制啟用 (`llm_service.py`)
- 修改聊天功能 LLM 配置預設值為 `True`
- 強化系統提示詞，強調需求理解和商品搜尋
- 增強無商品時的禮貌回覆邏輯

### 2. 聊天處理器優化 (`chat_router_goods_action.py`) 
- 強制優先使用 LLM 聊天模式
- 增加商品目錄搜尋範圍 (200 項商品)
- 新增增強的回退響應函數 `_create_enhanced_fallback_response()`
- 改善錯誤處理，確保即使 LLM 失敗也保持智能互動

### 3. 應用程式配置 (`app.py`)
- 新增強制聊天模式標記 `USE_CHAT_MODE_FORCED`
- 確保系統預設啟用所有 LLM 功能

### 4. 環境變數配置 (`.env.llm_mandatory`)
- 創建專門的 LLM 強制模式配置文件
- 預設啟用所有必要的 LLM 功能

## 🎯 功能特色

### ✅ **強制 LLM 互動**
- 所有使用者訊息都經過 LLM 處理
- 即使 API 不可用也有智能回退模式
- 保持對話的自然性和專業性

### 🔍 **智能需求理解**
- LLM 深度分析使用者的商品需求
- 提取關鍵字、預算、用途等資訊
- 基於理解進行精準商品搜尋

### 🛒 **商品搜尋整合**
- 直接搜尋 VIEW_GOODS_enhanced.csv
- 支援模糊匹配和精確搜尋
- 提供特價資訊和商品詳情

### 💬 **禮貌無商品回覆**
- 沒有合適商品時提供詳細說明
- 主動建議替代方案
- 引導使用者提供更多需求資訊

### 🔄 **現有模式兼容**
- 保留所有現有的商品推薦功能
- 支援生日聚會等複雜場景
- 維持建議系統和快取機制

## 🚀 使用方式

### 環境配置
```bash
# 設置有效的 OpenAI API Key（必要）
export OPENAI_API_KEY=sk-your-real-api-key-here

# 可選：覆寫預設聊天/搜尋 LLM 旗標
export CHAT_USE_LLM_EXPAND=True
export CHAT_USE_LLM_INTENT=True
export CHAT_USE_LLM_RERANK=False
export CHAT_USE_LLM_PROMO=True

export SEARCH_USE_LLM_EXPAND=False
export SEARCH_USE_LLM_INTENT=False
export SEARCH_USE_LLM_RERANK=False
export SEARCH_USE_LLM_PROMO=False
```

### 設定驗證
```bash
curl -s http://localhost:8000/api/debug/llm | python3 -m json.tool
# 應看到：client_available: true, openai_api_key_status: valid_key_****
```

### 測試互動範例

#### 情境 1：有符合商品
```
使用者：我想要健康的早餐麥片
LLM 回應：根據您對健康早餐麥片的需求，我為您找到了 3 款相關商品...
```

#### 情境 2：無符合商品  
```
使用者：我要買電子產品
LLM 回應：很抱歉，目前我們暫時沒有電子產品類別的商品。不過我們有多款...
```

#### 情境 3：需求不明確
```
使用者：你好
LLM 回應：歡迎來到哈通友善生活館！請告訴我您想要什麼類型的商品...
```

## 📊 技術架構

```
使用者訊息
    ↓
強制 LLM 處理
    ↓
需求理解 & 關鍵字提取
    ↓
VIEW_GOODS_enhanced.csv 搜尋
    ↓
有商品 → 智能推薦 + 詳細資訊
無商品 → 禮貌說明 + 替代建議
    ↓
維持對話連續性
```

## 🔧 故障處理

### LLM API 不可用時
- 自動切換到增強回退模式
- 仍保持需求理解能力
- 提供基本商品搜尋功能

### 商品資料問題時  
- 優雅降級到基本回覆
- 引導使用者提供更多資訊
- 保持專業和禮貌的語調

## ✨ 優勢特色

1. **100% LLM 覆蓋**：確保所有互動都經過 AI 處理
2. **智能需求分析**：深度理解使用者真正需要的商品
3. **精準商品匹配**：基於 CSV 資料提供最適合的推薦
4. **人性化無商品處理**：專業且貼心的回應方式
5. **系統穩定性**：多層回退機制保證服務可用性

這個修改方案完全符合您的需求，確保系統一律透過 LLM 與使用者互動，智能理解商品需求，並提供專業的購物建議服務。
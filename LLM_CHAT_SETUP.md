# 啟用 LLM 聊天模式設定指南

## 問題診斷

聊天模式沒有啟動真正的 LLM 模型互相交談的原因：

1. **無效的 API Key**: 當前 `OPENAI_API_KEY=your-openai-api-key` 是佔位符
2. **未使用 LLM 聊天功能**: 之前使用簡化的規則式回應

## 解決方案

### 1. 設置真實的 OpenAI API Key

更新 `.env` 文件或在 Render 環境變數中設置：

```env
OPENAI_API_KEY=sk-your-real-openai-api-key-here
```

### 2. 已整合的 LLM 聊天功能

修改後的聊天處理器現在會：

1. **優先使用 LLM 聊天**: 調用 `chat_reply` 函數進行真正的 AI 對話
2. **回退到特殊場景處理**: 生日聚會等複雜場景
3. **基本商品搜索**: 簡單的商品查詢
4. **最終簡單處理器**: 確保系統穩定性

### 3. LLM 聊天功能特點

- **真正的對話**: 使用 ChatGPT 進行自然語言交流
- **商品知識**: 基於商品目錄提供專業建議  
- **上下文記憶**: 支援多輪對話歷史
- **商品對齊**: 自動識別並推薦相關商品

## 測試 LLM 聊天

### 有效 API Key 時的期望行為：

```bash
# 自然對話
POST /api/chat
{"message": "你好，我想要一些健康的零食"}

# 期望回應：真正的 AI 對話，而不是制式回應
{
  "reply": "您好！我很樂意為您推薦一些健康的零食選擇。我們有多款無糖餅乾和天然堅果類商品...",
  "suggestion_ids": ["4718018351743", ...],
  "session_id": "abc12345"
}
```

### 無效 API Key 時的行為：

```bash
# 回退到規則式處理
{
  "reply": "我找到 X 款商品，例如...",
  "suggestion_ids": [...],
  "session_id": "abc12345"
}
```

## 配置檢查清單

- [ ] 設置有效的 `OPENAI_API_KEY`
- [ ] 確認 `USE_CHAT_MODE=True`
- [ ] 確認 `CHAT_OPENAI_MODEL=gpt-4o-mini`
- [ ] 部署更新到 Render
- [ ] 測試自然語言對話

## 成本考量

- **GPT-4o-mini**: 成本較低，適合生產使用
- **對話頻率**: 可考慮添加使用限制
- **回退機制**: 確保 API 額度用完時仍可正常工作

## 立即行動

1. 在 Render 環境變數中設置真實的 `OPENAI_API_KEY`
2. 重新部署服務
3. 測試聊天功能是否啟用 LLM 對話
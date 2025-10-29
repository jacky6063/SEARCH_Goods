# 啟用 LLM 聊天模式設定指南

## 配置狀態 ✅

LLM 聊天模式配置已完成：

1. **✅ 有效的 API Key**: Render 環境已設定真實的 `OPENAI_API_KEY`
2. **✅ LLM 聊天功能**: 系統已整合完整的 AI 對話功能
3. **✅ 回退機制**: 多層處理確保系統穩定性

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

- [x] 設置有效的 `OPENAI_API_KEY` ✅ **已在 Render 完成**
- [x] 確認 `USE_CHAT_MODE=True` ✅
- [x] 確認 `CHAT_OPENAI_MODEL=gpt-4o-mini` ✅
- [ ] 部署更新到 Render
- [ ] 測試自然語言對話

## 成本考量

- **GPT-4o-mini**: 成本較低，適合生產使用
- **對話頻率**: 可考慮添加使用限制
- **回退機制**: 確保 API 額度用完時仍可正常工作

## 下一步驟

1. ✅ ~~在 Render 環境變數中設置真實的 `OPENAI_API_KEY`~~ **已完成**
2. 觸發 Render 重新部署（如果尚未自動部署）
3. 測試 LLM 聊天功能：
   ```bash
   # 測試自然語言對話
   curl -X POST https://your-render-app.onrender.com/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "你好，我想要一些健康的零食"}'
   ```

## 🎉 預期效果

現在聊天系統應該會：
- 使用真正的 ChatGPT 進行對話
- 提供自然的商品建議
- 支援複雜的購物需求分析
- 記住對話上下文
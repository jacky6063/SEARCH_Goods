# 搜索與聊天功能 LLM 配置分離

## 問題解決

原本搜索和聊天功能共用同一組 LLM 配置參數，導致：
- 當搜索功能正常時聊天功能連線失敗
- 當聊天功能正常時搜索功能連線失敗
- 無法獨立控制兩個功能的 AI 特性

## 解決方案

### 1. 分離的環境變數配置

#### 搜索功能 LLM 設定
```env
SEARCH_USE_LLM_EXPAND=True       # 查詢擴展
SEARCH_USE_LLM_INTENT=True       # 意圖分析  
SEARCH_USE_LLM_RERANK=False      # 結果重排序
SEARCH_USE_LLM_SHORTDESC=False   # 短描述生成
SEARCH_USE_LLM_PROMO=False       # 宣傳文案生成
SEARCH_OPENAI_MODEL=gpt-4o-mini  # 搜索專用模型
```

#### 聊天功能 LLM 設定
```env
CHAT_USE_LLM_EXPAND=True         # 查詢擴展
CHAT_USE_LLM_INTENT=True         # 意圖分析
CHAT_USE_LLM_RERANK=False        # 結果重排序
CHAT_USE_LLM_SHORTDESC=False     # 短描述生成
CHAT_USE_LLM_PROMO=False         # 宣傳文案生成
CHAT_OPENAI_MODEL=gpt-4o-mini    # 聊天專用模型
USE_CHAT_MODE=True               # 聊天模式開關
CHAT_SYS_MAX_ITEMS=200           # 聊天系統商品上限
```

### 2. 向後相容性

保留原有環境變數以確保現有系統繼續工作：
```env
USE_LLM_EXPAND=True
USE_LLM_INTENT=True
USE_LLM_RERANK=False
USE_LLM_SHORTDESC=False
USE_LLM_PROMO=False
OPENAI_MODEL=gpt-4o-mini
CHAT_MODEL=gpt-4o-mini
```

### 3. 函數 API 更新

所有 LLM 服務函數新增 `use_search_config` 參數：

```python
# 使用搜索配置
llm_expand_query(query, use_search_config=True)
llm_analyze_query(query, use_search_config=True)
llm_shorten_20(text, use_search_config=True)
llm_generate_promo(name, desc, use_search_config=True)
llm_rerank_products(..., use_search_config=True)

# 使用聊天配置
llm_expand_query(query, use_search_config=False)
llm_analyze_query(query, use_search_config=False)
# ... 其他函數同理
```

## 配置範例

### 場景 1：搜索啟用 AI，聊天純規則式
```env
SEARCH_USE_LLM_EXPAND=True
SEARCH_USE_LLM_INTENT=True
SEARCH_USE_LLM_SHORTDESC=True

CHAT_USE_LLM_EXPAND=False
CHAT_USE_LLM_INTENT=False
CHAT_USE_LLM_SHORTDESC=False
```

### 場景 2：聊天啟用 AI，搜索基礎功能
```env
SEARCH_USE_LLM_EXPAND=False
SEARCH_USE_LLM_INTENT=False
SEARCH_USE_LLM_RERANK=False

CHAT_USE_LLM_EXPAND=True
CHAT_USE_LLM_INTENT=True
CHAT_USE_LLM_RERANK=True
```

### 場景 3：兩者都使用不同模型
```env
SEARCH_OPENAI_MODEL=gpt-3.5-turbo
CHAT_OPENAI_MODEL=gpt-4o-mini
```

## 測試驗證

1. **搜索功能測試**：
   ```bash
   curl -H 'Content-Type: application/json' \
        -d '{"query":"餅乾","topn":3}' \
        https://search-goods-api.onrender.com/api/search
   ```

2. **聊天功能測試**：
   ```bash
   curl -H 'Content-Type: application/json' \
        -d '{"message":"餅乾"}' \
        https://search-goods-api.onrender.com/api/chat
   ```

## 實施狀態

✅ 環境變數分離
✅ LLM 服務函數更新
✅ 搜索 API 使用搜索配置
✅ 聊天 API 使用聊天配置
✅ 向後相容性保持
✅ 基本功能測試通過

## 注意事項

1. 兩個功能現在可以獨立配置，互不影響
2. 可以使用不同的 OpenAI 模型以優化成本和性能
3. 聊天功能包含多層錯誤處理，確保即使複雜 AI 系統失敗也能提供基本服務
4. 配置更改需要重啟服務才能生效

## 成效

- ✅ 解決了搜索和聊天功能互相衝突的問題
- ✅ 允許靈活的 AI 特性開關組合
- ✅ 保持系統穩定性和向後相容性
- ✅ 搜索功能正常運作（已測試）
- ✅ 聊天功能基本運作（已測試）
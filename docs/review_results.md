# 審查結果報告

## 測試摘要
- `pytest backend/tests -q`
  - 結果：全部通過（10 passed），但 FastAPI `@app.on_event` 產生棄用警告。

## 重要發現
1. **FastAPI 啟動事件使用已棄用 API**  
   - `backend/app.py` 仍使用 `@app.on_event("startup")` 進行資料預熱。FastAPI 官方建議改用 lifespan handlers，以避免未來版本中功能被移除的風險。  
   - 影響：目前僅產生警告，但長期會造成維護問題。

2. **商品過濾邏輯的重複條件**  
   - `search_products` 內對於醬油類關鍵字的處理重複新增 `["醬油", "蔭油"]` 至 `name_filter_keywords`。  
   - 影響：邏輯上無害，但會生成重複的正則片段，影響可讀性與後續維護。

3. **未使用的 `singled_terms` 暗示遺留邏輯**  
   - `search_products` 開頭建立的 `singled_terms` 從未在函式後續使用，可能是早期分類補強策略的遺留程式碼。  
   - 建議：確認是否有遺漏的功能，或移除死碼以保持程式乾淨。

## 建議
- 將 FastAPI 啟動流程改寫為 lifespan context manager。  
- 整理 `search_products` 內的條件與變數，避免重複及死碼。  
- 持續關注 pytest 輸出，確保未出現新的警告或失敗。

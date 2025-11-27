# Hot Chips + Categories CSV 延續開發備忘錄

更新日期：2025-11-06  
撰寫目的：提供下一階段開發與驗收參考，聚焦熱門分類（chips）改版與 goods_categories.csv 單一資料源。

---

## 1. 目標與原則
- 熱門分類（L1/L2/L3）僅由 `goods_categories.csv` 提供，**不再**從商品資料推導。
- API 與前端資訊顯示 **不再帶 count**，僅顯示名稱，避免混亂。
- `context.label` 需穩定地傳回「熱門分類｜熱門中分類（L1）｜熱門小分類（L1 > L2）」等字串，前端直接使用。
- 預設回傳全量資料；若要限制，使用 `top_k` 明確指定。UI 使用「更多/收合」管理視覺展示。

---

## 2. 現況總結（2025-11-06）

### 後端
- `backend/services/categories_service.py`
  - 來源：`CATEGORIES_PATH`（預設 `data/goods_categories.csv`），支援 `CATEGORIES_CACHE_TTL` 快取。
  - 正規化：全形 `／` → 半形 `/`，多餘空白合併；生成 `_L1n/_L2n/_L3n` 供寬鬆比對。
  - `get_scope(level, parent_l1?, parent_l2?, top_k?)` 回傳：
    - `items=[{"name": ...}]`
    - `total` / `more_count` / `top_k`
    - `context = {level, parent_l1, parent_l2, label}`
  - CSV 缺失或解析錯誤會記錄 `last_error` 並回傳空集合（HTTP 200）。
- `/api/catalog/scope`
  - 直接呼叫 `categories_service.get_scope`。
  - `top_k <= 0` 或未傳 ⇒ 回傳全量。
  - 失敗時回傳空陣列與對應 `context`。
- `/api/chat` 導覽流程（`chat_router_goods_action.py`）
  - L1/L2 名稱保留斜線（`/`、`／`）；比對區長度擴大到 40 字。
  - 導覽（L1→L2→L3）優先於概覽回覆；overview 問句不會覆寫導覽。
  - `meta.available_scope` 告知前端下一層可展示的名稱清單。
- `/api/search`
  - 支援 `category_hierarchy = {L1,L2,L3}` 過濾。
  - 支援 `prefer_special_first`：優先顯示有特價的商品（穩定排序）。

### 前端（`frontend/index.html`）
- 初始化 chips
  - `window.addEventListener('load', ...)` 會呼叫 `setHotScopePath({L1:null,L2:null,L3:null})` 後 **一次** `loadHotCategories(8)`（Top-8）。
  - `setMode('chat')` 仍會呼叫 `loadHotCategories(0)`，切回聊天模式時會重新抓取資料。
  - `window.latestAvailableScope` 若有資料（聊天 meta 回傳）會優先渲染該層級。
- chips 呈現
  - 標題優先採用 `scope.context.label`；僅在 `hotScopePath` 有父層時顯示「返回上一層」。
  - `items` 僅顯示名稱；沒有數量。
  - `更多 (+N)` 會把 `topK` 加倍後重新載入；目前沒有針對桌面/手機的不同預設展開狀態。
- 互動行為
  - L1 chip：送出 `你們有什麼{L1}的品類？`，並更新 `hotScopePath.L1`。
  - L2 chip：送出 `在{L1}下我對{L2}有興趣...`，更新 `hotScopePath.L2`。
  - L3 chip：直接 POST `/api/search`，帶入 `category_hierarchy` 及 `prefer_special_first=true`；若無結果會自動再查一次（關閉特價優先）。

### 已知落差 / TODO
- `setMode('chat')` 每次仍會觸發 `loadHotCategories(0)`，若要避免重複請求需新增「已初始化」旗標。
- 目前未實作 `__scopeInitialized` / `hotScopeReqId` 防併發邏輯（舊文件描述但程式尚未導入）。
- chips 並未區分桌面 / 手機的預設展開狀態（僅透過「更多」延伸清單）。

---

## 3. goods_categories.csv 需求
- 必備欄位：`L1`（必填）、`L2`、`L3`、`Enabled`、`DisplayOrder`。
- `Enabled` 支援 `true/false/1/0/yes/no`，預設 `true`。
- `(L1, L2, L3)` 應唯一；僅輸出 Enabled=真 的列。
- 排序：先依 `DisplayOrder` 升冪（`None` 視為最大），再以名稱字母順序。
- 父層比對使用 `_norm_name`（全形斜線轉半形、trim、多空白合併）。

---

## 4. 相關環境變數
- `CATEGORIES_PATH`（預設 `data/goods_categories.csv`）
- `CATEGORIES_CACHE_TTL`（預設 300 秒）
- 搜尋排序參數（現有設定）：`HIER_SORT_WEIGHT`、`RERANK_SORT_WEIGHT`、`SEARCH_USE_LLM_RERANK`

---

## 5. API 快照

### GET `/api/catalog/scope`
- Query：`level=L1|L2|L3`、`parent_l1?`、`parent_l2?`、`top_k?`
- Response：
  ```json
  {
    "level": "L2",
    "total": 12,
    "top_k": 12,
    "more_count": 0,
    "items": [{"name": "五穀/豆類/米麵/乾貨"}, ...],
    "context": {
      "level": "L2",
      "parent_l1": "常溫食品",
      "parent_l2": null,
      "label": "熱門中分類（常溫食品）"
    }
  }
  ```

### POST `/api/chat`
- 導覽訊息會回傳 `display_mode = text_only`，並在 `meta.available_scope` 提供下一層清單。

### POST `/api/search`
- 新增 `category_hierarchy` 與 `prefer_special_first`。
- 0 筆結果時訊息維持禮貌回覆，可由前端觸發回退查詢。

---

## 6. 前端互動流程
1. 首次載入 → `loadHotCategories(8)` 取得 L1 chips。
2. 點 L1 → 送聊天訊息並等待回覆，同時本地更新 `hotScopePath.L1` 再觸發 `loadHotCategories(0)`。
3. 點 L2 → 同上，更新 `hotScopePath.L2`。
4. 點 L3 → 直接進搜尋模式，商品列表依特價優先。
5. 後續若 LLM 回傳 `available_scope`，前端優先採用該資料渲染對應層級。

---

## 7. 測試與驗收建議
- 準備 `data/goods_categories.csv`（或設定 `CATEGORIES_PATH`），重啟後端或 POST `/api/admin/clear-cache`。
- 驗證 API：
  - `GET /api/catalog/scope?level=L1`
  - `GET /api/catalog/scope?level=L2&parent_l1=常溫食品`
  - `GET /api/catalog/scope?level=L3&parent_l1=常溫食品&parent_l2=五穀/豆類/米麵/乾貨`
- 前端手動驗收：
  - 首屏僅 L1，無返回按鈕。
  - L1 → 標題「熱門中分類（常溫食品）」。
  - L2 含斜線仍可進入 L3。
  - L3 chips → 搜尋頁面，若 0 筆會自動再查一次。

---

## 8. 常見問題排查
- **首屏同時出現 L1/L2**：檢查是否有額外腳本（如 `patches/auto_boot.js`）呼叫 `loadHotCategories`；目前仍有多處呼叫需統一管理。
- **含斜線的 L2 進不了 L3**：檢查 CSV 是否有對應 L3、`Enabled` 是否為真。
- **scope 空白**：確認 `CATEGORIES_PATH` 指向正確檔案、檔案編碼 UTF-8 / UTF-8 with BOM 可被正確解析。

---

## 9. 建議後續優化
1. 新增 `__scopeInitialized` / `hotScopeReqId`，避免重複或交錯請求。
2. 調整 `setMode('chat')` 為可選是否刷新 chips（或僅首次初始化）。
3. 針對桌面 / 手機提供差異化的 chips 展開策略與 UI 提示。
4. 後台 `/api/admin/info` 增加 categories 訊息（路徑、筆數、匯入時間、錯誤狀態）。
5. 新增 `/api/admin/upload-categories` 以利管理端上傳。

---

## 10. 部署提醒
- 確保部署環境設定 `CATEGORIES_PATH` 指向正確 CSV。
- 每次更新 CSV 後記得重啟後端或呼叫 `/api/admin/clear-cache`。
- 前端部署如遇快取，可清除 Netlify CDN 或調整資源版本號。


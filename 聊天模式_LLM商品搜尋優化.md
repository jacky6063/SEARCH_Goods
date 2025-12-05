# 聊天模式 LLM 商品搜尋優化建議

## 不在範圍
- 不重構專案架構、路由設計、目錄結構。
- 不改 LLM 模型與金鑰設置；不硬編 API Key。

## 禁止事項（務必遵守）
- **禁止重構整個專案**：不得主動改動架構、路由、目錄，除非任務卡明確要求。
- **禁止修改既有商業邏輯**：不得更動商品搜尋/訂單/會員/價格/庫存與 DB schema。
- **禁止硬編 API Key / 機敏資訊**：所有金鑰一律用環境變數，提示詞/程式碼不可寫死。
- **一次只執行一張任務卡**：不得偷跑下一張卡的內容。
- **不確定時少改**：無法判斷時，優先加註解/提議，不要大改。
- **不執行的命令**：不得使用 `git reset --hard`、`git checkout -- .`、`rm -rf /` 等破壞性指令；不得清除非本任務相關檔案。

針對近期「禮盒」、「女款運動鞋」等案例，整理 LLM 在聊天模式下的搜尋/對齊優化重點與落地步驟。

## 目標
- 讓 LLM 的「意圖解析 → 搜尋條件 → 回覆」鏈路更準確，減少非相關商品混入。
- 保持意圖層輕量，資料驅動（分類/商品上新不用改碼）。

## 優化建議
1) **意圖解析輸出強化**
   - 系統提示增加：若命中「禮盒/伴手/送禮」→ `category_terms=["禮盒"]`、`required_terms=["禮盒"]`、`category_hierarchy` 指向禮盒相關 L3，信心值 > 0.6。
   - 性別映射：女款/女生/女用 → `gender=female`；男款/男生/男用 → `gender=male`。輸出固定欄位（可放在 `required_terms` 或獨立 `gender`）。
2) **搜尋前置規則**
   - 在 `chat_reply` 組 `structured_filters` 時，將 `required_terms` 映射為 `must_have_keywords`，同時帶入 `category_hierarchy`、`category_filter`、`gender`。
   - 禮盒場景：若 query/intent 含「禮盒/伴手」且無明確分類，也強制注入 `must_have_keywords=["禮盒"]`。
   - 性別場景：若 gender=female/male，則 `must_have_keywords` 加入女/男同義詞，並在結果無匹配時觸發缺貨回覆。
3) **打分/過濾修正**
   - `score_row`：備註加分僅限長度 ≥2 的詞，排除單字「有」等噪音；核心詞（禮盒/伴手/女款/男款）加權。
   - `_apply_structured_filters`：先跑 must-have 再跑排除詞，確保核心詞約束。
4) **LLM Guardrail**
   - `_mock_or_real_llm` system prompt 增加：若候選商品名稱/分類未含 must-have 關鍵詞（如禮盒/女款），應返回「暫無符合，是否改查詢或看相近品類」而非硬推單品。
   - 澄清策略：意圖信心 <0.55 時，優先詢問用途/性別/預算再搜尋。
5) **缺貨/兜底**
   - 禮盒：must-have 後若空結果，明確回「目前沒有禮盒」，並提供選項（相近禮盒/改單品/改價位）。
   - 性別：若 gender=female 但無女款，回「目前無女款，需看通用或男款嗎？」。
6) **動態分類提示**
   - `_build_category_hierarchy_prompt` 改為從 `goods_categories.csv`/商品資料動態生成分類與範例，避免硬編碼；意圖解析可自動認知新業種。

## 意圖解析層的維運策略
- 不必因商品數上千而膨脹意圖層；保持「薄、穩、資料驅動」：
  - 意圖解析只抽欄位（category_terms / required_terms / category_hierarchy / gender / price_range），不餵全量商品。
  - 商品與分類擴充靠資料（CSV/索引），非改程式碼；提示詞使用動態分類生成。
- 調整節奏：事件觸發 + 輕量週期檢視
  - 事件：錯配/召回差、上新業種/新欄位、模型替換、查詢分佈變化時立即微調提示或映射表。
  - 週期：每 2~4 週跑回歸案例檢視澄清率/非相關比例，微調同義詞映射、must-have/排除詞、性別/價格提取提示。
- 成本控制：LLM 只看少量候選/分類樹；搜索層用索引/規則處理大規模商品。

## LLM 的角色定位
- 理解：解析品類/性別/用途/價位，產出 `category_terms`、`required_terms`、`category_hierarchy`、`gender` 等欄位。
- 擴展：同義詞/關鍵詞擴展，提高召回。
- 澄清：信心低時提出針對性問題（用途/性別/預算），避免亂推。
- 對齊/重排（輕量）：對少量候選做語義檢核或重排，確保語境一致；命中 must-have 失敗時回缺貨訊息。
- 文案：把結構化候選轉成一致口吻的回覆/商品卡摘要。
- 守門：當無匹配或違反 must-have（女款缺貨、禮盒缺貨）時，產生「缺貨/改查詢」的安全回覆而非硬湊。

## 影響範圍（程式位置）
- `backend/llm_service.py`
  - `llm_analyze_query` 系統提示增補（禮盒/性別規則）。
  - `_prepare_chat_context` / `chat_reply`：將 `required_terms`→`must_have_keywords`、`category_hierarchy`、`gender` 帶入 `structured_filters`。
  - `_mock_or_real_llm`：guardrail（無符合 must-have 時拒絕亂推）。
- `backend/goods_search_service.py`
  - `score_row`：備註加分長度門檻，核心詞加權。
  - `_apply_structured_filters`：確保 must-have 優先。
- `backend/llm_service.py`（若採用動態分類方案）
  - `_build_category_hierarchy_prompt` 改為資料驅動。

## 驗證建議
- 回歸案例（固定檢測）
  - 禮盒/伴手：應只出現含「禮盒」的商品，若無則明說缺貨。
  - 女款運動鞋：結果需含女款關鍵詞，無則觸發缺貨詢問。
  - 男款皮帶、價位範圍、無庫存情境：確認澄清/缺貨文案正常。
- 觀察指標
  - must-have 命中率、澄清觸發率、非相關商品比例、回覆時延。

## 實施順序（建議）
1. 調整 `score_row` + `_apply_structured_filters`（最小風險，先阻斷噪音）。
2. 在 `chat_reply` 注入 must-have（`required_terms`→`must_have_keywords`）與 gender/filter 傳遞。
3. 補充 `llm_analyze_query` 提示（禮盒/性別規則）。
4. 加入 LLM guardrail 缺貨文案。
5. 若有餘裕，再做動態分類提示詞改造。

## 任務卡（程式優化規劃）
1) 打分與過濾修正  
   - 調整 `backend/goods_search_service.py:score_row`：備註加分僅限長度 ≥2 的詞；核心詞（禮盒/伴手/女款/男款）加權；排除單字噪音。  
   - 確認 `_apply_structured_filters` 先跑 must-have，再跑排除詞。

2) 意圖→搜尋約束傳遞  
   - `backend/llm_service.py:chat_reply/_prepare_chat_context`：將 `required_terms` 映射到 `must_have_keywords`，帶入 `category_hierarchy`、`category_filter`、`gender` 至 `structured_filters`。  
   - 禮盒/伴手命中時，強制注入 `must_have_keywords=["禮盒"]`。

3) 意圖解析提示強化  
   - `llm_analyze_query` 系統提示增補：遇到禮盒/送禮/伴手 → 填 `category_terms=["禮盒"]`、`required_terms=["禮盒"]`、`category_hierarchy` 指向禮盒 L3、信心 >0.6；性別同義詞映射到 gender=female/male。  
   - 確保輸出固定欄位（category_terms/required_terms/category_hierarchy/gender）。

4) LLM Guardrail 與缺貨文案  
   - `_mock_or_real_llm` system prompt：若候選未含 must-have（如禮盒/女款），返回缺貨/改查詢，不得硬推。  
   - 缺貨策略：禮盒空 → 提示無禮盒並給選項；gender 空 → 提示無女款/男款並詢問是否看通用或改查詢。

5) 動態分類提示（可選/後續）  
   - `_build_category_hierarchy_prompt` 資料驅動：從 `goods_categories.csv`/商品資料生成分類與範例，移除硬編碼。

6) 驗證與回歸  
   - 建立並執行回歸用例：禮盒/伴手、女款運動鞋、男款皮帶、價位段、無庫存情境。  
   - 觀察：must-have 命中率、非相關比例、澄清/缺貨觸發率、回覆時延。


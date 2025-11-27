# LLM 真人客服進階設計任務卡

版本: v1.0  
建立日期: 2025-11-18  
依據文件: CODE_REVIEW_商品聊天模式_20251116.md

—

一、背景與目標
- 目標: 以「真人客服銷售員」角色，運用 LLM+規則的混合智慧，快速理解客人需求、縮小範圍、精準推薦公司自有商品；對於非銷售範圍 (OOS) 的需求，以禮貌與專業的方式即時辨識與回覆。
- 關鍵指標 (KPI):
  - 轉化前置指標: 平均澄清輪數 ≤ 2；從開聊到出第一版精準清單 ≤ 1 回合。
  - 商品匹配品質: Top-3 命中率 ≥ 70%，OOS 誤推薦率 ≤ 2%。
  - 體驗: 首屏回覆 < 1.5s（開啟串流時 < 500ms 首字）；「禮貌/專業」評分 ≥ 4.5/5。

—

二、現況總覽（已完成架構）
依據 CODE_REVIEW_商品聊天模式_20251116.md：
- 入口層與路由
  - app.py: POST /api/chat → chat_handler
  - chat_router_goods_action.py: 對話編排與 Handler 設計，具遺留流程 _legacy_chat_flow
- 核心/服務
  - llm_service.py: chat_reply、意圖檢測、上下文產品詢問檢測、商品格式化、商品搜尋
  - services/content_engine.py: 角色與模板、AI 內容生成
  - conversation_core/: Orchestrator、IntentRouter、HandlerBase、資料模型
  - conversation_flow_manager.py: 多輪對話狀態管理（生日聚會場景）
  - 支援服務: catalog_service、bundle_service、search_service、chat_logging_bridge
- 特色能力
  - 混合智慧：規則 + LLM，具多層回退
  - 意圖檢測：company_info / information / product_search / general 等
  - 上下文理解：對話中「這個/那個」的語義續接
  - 商品結果格式化：結構化輸出、前端友好
  - OOS 檢測雛形：超出銷售範圍時避免誤導
- 主要不足（與真人客服銷售員要求相比）：
  - 缺少銷售商品「分類知識庫」與同義詞映射（真人客服需很清楚分類）
  - 缺少「澄清/縮小範圍」的標準化槽位流程（類型/顏色/款式/價位…）
  - OOS 決策需更明確與即時（第一時間判斷不售）
  - Handler 層未有專職 SalesAssistant 流程（目前偏向一般商品搜尋/資訊）
  - 缺統一日誌、測試、快取與串流強化

—

三、差距與痛點
1) 產品分類知識缺口
- 缺正式 taxonomy（類別 → 子類別 → 可篩屬性）與同義詞、禁售/不售清單
2) 對話澄清流程缺口
- 未定義各分類的最小必要槽位（例：女用包包 → 子類型/顏色/款式/價格區間）
3) OOS 判斷缺口
- 缺快速判斷「不在公司銷售範圍」的輕量規則與禮貌模板
4) Handler/路由缺口
- 缺 SalesAssistantHandler（銷售導購專用），意圖優先級需調整
5) 產出形態缺口
- 缺「首屏澄清 + 可點選 chips + 立即可購清單（TopN）」的統一格式
6) 工程實務
- 日誌規範、OpenAI 客戶端快取、測試覆蓋、串流、效能與觀測尚待補強

—

四、解決方案設計（概要）
A. 銷售分類知識庫（SalesKnowledgeService）
- 內容：
  - taxonomy.json: 公司可售類別 → 子類別 → 可篩屬性（顏色/材質/尺寸/價位…）
  - synonyms.json: 類別/子類別/屬性的同義詞、口語說法（例：側背=斜背；黑=墨黑）
  - oos_categories.json: 不售類別白名單（例：3C、家電、機車…）
  - attribute_values.json: 屬性候選值與正規化（例：顏色、材質）
- 能力：
  - 類別/屬性標準化、同義詞映射；OOS 即時判斷
  - 對外 API: normalize(query) → {category, sub_type, attributes, is_oos}

B. 銷售助手處理器（SalesAssistantHandler）
- 定位：專職處理「我要買X」的導購場景
- 流程：
  1) 解析查詢 → 類別/子類別/屬性意圖 → OOS 守門
  2) 槽位收集：依該分類最小必要槽位，使用最少問題完成澄清
  3) 生成 TopN 推薦清單（search_service + 槽位過濾 + 人氣/評分排序）
  4) 以真人口吻輸出（LLM 調整語氣/補充使用建議），附可點選 chips
- 產出 payload：
  - filters/slots、topn_products、chips（快速修改條件）、explanations（為何推薦）

C. 槽位管理（SlotManager）
- 每個主類別定義「最低可售集」：
  - 女用包包: {子類型、顏色、款式、價位區間}；可選：尺寸、材質、品牌、用途
  - 延伸到其他類別（鞋、服飾、食品、居家…）
- 策略：
  - 先用規則與知識庫最大化填充；缺口最少提問（一次 1~2 個）
  - 歧義情境請 LLM 產生人性化提問語句（避免機械口吻）

D. OOS 守門（OOSGuard）
- 即時判斷是否屬於不售類別（如 3C、家電）
- 禮貌模板：先說明不售，再提供我們可售的相近/替代類別（若有）

E. 統一回應格式（ResponseFormatter）
- reply: 真人客服語氣文本（可串流）
- payload: {products[], filters{}, chips[], next_required_slots[]}
- 日後可擴充：分區塊摘要 + 詳細展開

F. Prompt 與安全策略
- Persona：小哈（專業、親切、自然）
- Guardrails：
  - 不可承諾公司不存在/不售的商品
  - 有疑慮回退到規則結果；敏感內容拒答
  - 優先使用知識庫與搜尋結果，LLM 只用於語氣與解釋

G. 觀測與效能
- 結構化日誌（structlog）、OpenAI 客戶端快取、串流回覆
- 指標：命中率、澄清輪數、首屏延遲、OOS 誤導率、TopN 點擊/加購

—

五、互動示例（女用包包）
- 使用者: 「我要買女用包包」
- 系統（SalesAssistantHandler）首輪：
  - reply: 「了解！我們的女用包包有托特、斜背、手提、後背…想先鎖定哪一類呢？另外偏好顏色或預算區間嗎？」
  - chips: [托特, 斜背, 手提, 後背] + [黑/棕/米白] + [1000-2000, 2000-4000]
  - next_required_slots: [sub_type, color, price_range]
- 使用者: 「斜背包，想要黑色，預算 2,000-3,000」
- 系統：
  - 過濾搜尋、TopN=5；
  - reply: 「根據你偏好『黑色斜背、2,000-3,000』，這 5 款最符合，也各有不同收納與背帶寬度。我先列出兩款輕便好搭款，另外三款容量較大、通勤實用。」
  - payload.products: [商品列表]
  - chips: [改顏色: 棕/米白, 提升預算, 換款式: 托特]

—

六、配置檔案（範例）
- config/taxonomy/categories.json
  - women_bag → {sub_types: [tote, crossbody, handbag, backpack], attributes: {color, style, material, size, price_range}}
- config/taxonomy/synonyms.json
  - {"斜背": ["側背", "crossbody"], "黑": ["黑色", "墨黑"]}
- config/taxonomy/oos_categories.json
  - ["3C", "家電", "機車", "保險"]
- config/taxonomy/attribute_values.json
  - color: [黑, 棕, 米白, 海軍藍, 酒紅]

—

七、任務分解與優先級（P0 → P2）
P0 基礎可用（1~2 週）
1. 建立銷售分類知識庫（SalesKnowledgeService）
- 交付: config 檔（categories.json、synonyms.json、oos_categories.json、attribute_values.json）；載入器與快取
- 驗收: 給定查詢可正規化類別/子類別/屬性；OOS 判斷正確率 ≥ 95%（測試集）

2. 新增 SalesAssistantHandler（最小可用）
- 能力: 解析分類 → 最小槽位澄清（1~2 問）→ 搜尋過濾 → TopN 推薦 → 真人口吻回覆與 chips
- 驗收: 對「女用包包」等核心類別能於第二輪產出 TopN；回覆不包含不售類別

3. OOSGuard 與禮貌模板
- 能力: 第一時間辨識不售類別並回覆；若可能提供相近替代類別
- 驗收: 對「我要買3C產品」立即正確回覆不售，並列出公司有售大類

4. 意圖與路由調整
- 將 sales_consulting（導購）優先於一般 product_search；或合併為 product_search，但加 can_handle 的分類規則
- 驗收: 「我要買女用包包」進入 SalesAssistantHandler，而非 general/legacy flow

5. 日誌與 OpenAI 客戶端快取
- 移除 print，統一 logging/structlog；OpenAI client 快取避免頻繁重建
- 驗收: 產線可依 session_id 追蹤全程；監看儀表板可見關鍵指標

P1 進階體驗（2~4 週）
6. SlotManager（動態槽位）
- 能力: 依類別載入最小槽位與候選值；缺口提問策略；LLM 生成自然澄清語句
- 驗收: 多類別（包、鞋、服飾、食品）澄清輪數 ≤ 2

7. 目錄映射與排序
- search_service 過濾 + 規則排序（熱銷/評分/新品加權），必要時嵌入向量近似
- 驗收: Top-3 命中率 ≥ 70%

8. 回應串流與前端 chips 協定
- 能力: 首屏串流文字 + chips/payload 分離回傳；支援二次篩選 chips 互動
- 驗收: 首字 < 500ms；chips 可即時更新結果

9. 測試與 QA
- 單元: 意圖、OOS、正規化、槽位策略、排序
- 集成: 兩輪內完成導購；OOS 路徑；回退模板

P2 成熟與擴展（1~2 月）
10. 個人化與偏好記憶
- 記錄顏色/風格/尺碼偏好；下一次對談預設帶入

11. 高階搜尋與索引
- ES/向量資料庫；同義詞詞庫；屬性權重學習

12. A/B 與觀測平台
- 方案/Prompt/排序策略多版本實驗；線上監控

—

八、驗收與測試案例
- 意圖: 「我要買女用包包」→ sales_consulting；「我要買3C產品」→ OOSGuard
- 槽位: 缺子類型/顏色/價位時僅提問 1~2 個；回答後 1 回合出 TopN
- OOS: 對 3C/家電等立即禮貌拒絕並列出公司可售大類
- 效能: 串流首字 < 500ms；無串流時 < 1.5s 首屏

—

九、風險與緩解
- 幻覺/誤導: LLM 僅負責語氣與解釋；商品集合以規則/搜尋為準
- 覆蓋不足: synonyms 與屬性值逐步擴充；記錄未命中詞彙作離線補庫
- OOS 邊界: 以白名單/黑名單雙制；低置信時請求確認
- 效能: 客戶端快取、串流、熱門查詢快取、索引化

—

十、里程碑與工時（粗估）
- P0: 1~2 週（後端 1~2 人、測試 0.5 人）
- P1: 2~4 週（後端 2 人、前端 1 人、測試 1 人）
- P2: 1~2 月（後端 2~3 人、資料/搜索 1~2 人、前端 1 人）

—

十一、對外介面（回應資料結構建議）
- reply: string（可串流）
- payload:
  - products: [{id, name, price, url, image, reasons[]}]
  - filters: {category, sub_type, color, price_range, ...}
  - chips: [{type: filter|action, label, value}]
  - next_required_slots: [sub_type, color, price_range]
  - meta: {trace_id, intent, handler}

—

十二、Persona 與語氣要點（小哈）
- 親切、專業、自然；用詞口語化但不失禮
- 少量提問、逐步聚焦；避免一次拋大量選項
- 面對 OOS 先表理解與歉意，再提供公司可售範圍/替代方案

—

附錄 A：範例 OOS 回覆模板（簡）
- 「和你說明一下，我們目前沒有販售 3C/家電 類商品。不過在『配件/收納/生活用品』這幾個類別，我可以幫你快速找到實用又好搭的選擇，要不要先看看？」

# SEARCH_Goods — 專案流程總覽

## 🎯 專案目標

建立一個能用自然語言（含語音）查詢商品的客服查詢系統，支援：

* 🔍 **商品搜尋 / 關鍵字擴展**
* 🧠 **ChatGPT 輔助理解與摘要生成**
* 💬 **禮貌的空結果回覆**
* 📱 **桌面版＋手機版網頁 UI**
* 📦 **CSV 資料查詢後端 (FastAPI)**

---

## 🧱 系統架構概覽

```
SEARCH_Goods/
├─ backend/
│  ├─ app.py                    # FastAPI 主程式（含 /api/search）
│  ├─ goods_search_service.py   # 本地 CSV 搜尋、分數計算
│  ├─ llm_service.py            # ChatGPT 查詢展開與摘要生成 (可選)
│  ├─ requirements.txt
│  └─ .env                      # 含 OPENAI_API_KEY、DATA_PATH
│
├─ data/
│  └─ VIEW_GOODS_enhanced.csv   # 商品資料來源
│
├─ frontend/
│  └─ index.html                # 前端 UI (桌機+手機)
│
└─ README.md / FLOW_OVERVIEW.md # 說明與架構文件
```

---

## 🔄 資料與查詢流程圖

```
使用者輸入(或語音)
        │
        ▼
 [前端 index.html]
  - 送出查詢到 /api/search
  - 顯示載入中
        │
        ▼
 [FastAPI 後端 app.py]
  - 讀取 CSV (快取)
  - 呼叫 ChatGPT 展開查詢 (可選)
  - 送進 goods_search_service
        │
        ▼
 [goods_search_service]
  - 文字正規化
  - 欄位比對 (Name / Description / 分類)
  - 分數排序、取前 N 筆
  - 若無結果 → 禮貌回覆
        │
        ▼
  (可選) ChatGPT 摘要生成 20 字描述
        │
        ▼
  回傳 JSON 給前端
        │
        ▼
 [前端顯示結果卡]
  - 圖片 60x60、購物網址「點我連結」
  - 若空 → 顯示「很抱歉目前沒有找到符合您需求的商品🙏」
```

---

## 🧠 ChatGPT 串接點

| 階段   | 功能                   | 模型建議          | 範例函式                 | 輸出用途            |
| ---- | -------------------- | ------------- | -------------------- | --------------- |
| 查詢前  | Query Expansion 查詢展開 | `gpt-4o-mini` | `llm_expand_query()` | 增加召回率           |
| 查詢後  | 摘要生成（描述 ≤20字）        | `gpt-4o-mini` | `llm_shorten_20()`   | 填補 ShortDesc_20 |
| 查無資料 | 有禮貌回覆（不需 LLM）        | —             | `polite_fallback()`  | 穩定訊息輸出          |

> 📍 ChatGPT 僅用於語意強化，不生成價格或連結，所有資料仍來自 CSV。

---

## 🧩 API 流程（/api/search）

### Request

```json
POST /api/search
{
  "query": "外出 女用 包 休閒",
  "topn": 10
}
```

### Success Response

```json
{
  "message": "為您找到 3 項商品：",
  "items": [
    {
      "商品編號": "V55306F-0317",
      "商品名稱": "前扣式素雅休閒包-土黃色",
      "商品描述": "輕盈素雅、休閒百搭",
      "商品價格": "2,980",
      "商品特價": "",
      "商品購物網址": "https://example.com",
      "商品圖片網址": "https://example.com/img.jpg"
    }
  ]
}
```

### Empty Response

```json
{
  "message": "很抱歉，目前沒有找到符合您需求的商品喔 🙏 您可以嘗試其他關鍵字，或告訴我品牌、型號或預算範圍，我再幫您推薦合適的商品 💡 （目前查詢關鍵字：iPhone 17）",
  "items": []
}
```

---

## 🧮 搜尋邏輯（goods_search_service）

| 欄位             | 權重    | 備註            |
| -------------- | ----- | ------------- |
| Name 命中        | +2    | 商品名稱最重        |
| Description 命中 | +1    | 次要權重          |
| 分類/備註 命中       | +1    | 次要權重          |
| 特價商品           | +0.2  | 排序微調          |
| Min Score      | 1.5   | 過濾低相關度項目      |
| TopN           | 預設 10 | 可在 Request 傳入 |

---

## 💬 有禮貌回覆模板

```text
很抱歉，目前沒有找到符合您需求的商品喔 🙏
您可以嘗試其他關鍵字，
或告訴我品牌、型號或預算範圍，
我再幫您推薦合適的商品 💡
（目前查詢關鍵字：{{ query }}）
```

---

## 📱 前端互動規格

* **元件**

  * 🔹 輸入框 + 🎙️語音輸入 + 送出 + 重新對話
  * 🔹 桌面版：左側固定聊天區
  * 🔹 手機版：底部浮動操作列（Safe Area padding）
* **快捷鍵**

  * Enter → 送出
  * Ctrl/Cmd + K → 重新對話
  * Ctrl/Cmd + Shift + S → 語音輸入
* **可存取性**

  * `aria-live="polite"` 用於結果
  * `aria-label` 描述操作
* **語音**

  * Web Speech API (`webkitSpeechRecognition`)
  * 不支援時自動停用按鈕並提示

---

## ⚙️ 後端環境變數 (.env)

```
DATA_PATH=../data/VIEW_GOODS_enhanced.csv
OPENAI_API_KEY=你的ChatGPT金鑰
USE_LLM_EXPAND=True
USE_LLM_SHORTDESC=True
HOST=0.0.0.0
PORT=8000
```

---

## 🚀 啟動指令

```bash
# 1️⃣ 安裝依賴
cd backend
pip install -r requirements.txt

# 2️⃣ 啟動 FastAPI
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 3️⃣ 啟動前端預覽 (另一個終端)
cd ../frontend
python -m http.server 5173

# 打開 http://localhost:5173
# 確認 index.html 的 API_ENDPOINT = "http://localhost:8000/api/search"
```

---

## 🧠 系統工作流程摘要（10 秒版）

```
使用者輸入/語音 → /api/search
   ↓
(可選) ChatGPT 擴展查詢
   ↓
CSV 檢索 + 打分排序
   ↓
(可選) ChatGPT 生成 20 字摘要
   ↓
回傳 JSON
   ↓
前端渲染商品卡 or 禮貌回覆
```

---

## ✅ 驗收檢查表

| 項目  | 驗收內容                                  |
| --- | ------------------------------------- |
| API | `/api/search` 回傳正確格式（message + items） |
| LLM | 可開關 `USE_LLM_*` 參數，不影響主流程             |
| 前端  | 有送出、重新對話、語音輸入三按鈕                      |
| 空結果 | 顯示「禮貌回覆」                              |
| 響應式 | <=600px 手機單欄、底部浮動列                    |
| 快捷鍵 | Enter、Ctrl/Cmd+K、Ctrl/Cmd+Shift+S     |
| 安全  | 不輸出 API Key、不混生成價格/連結                 |

---

## 🧩 進階延伸（未來版）

* Docker Compose（FastAPI + Nginx）
* 日誌 + 召回統計
* ChatGPT 重新排序（ReRank 模型）
* 商品向量嵌入搜尋
* 將查詢行為接入 LINE 官方帳號 / FB Messenger Bot

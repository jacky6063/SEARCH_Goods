# SEARCH_Goods --- 整合式技術文件（v1.0）

內容包含：設計規格書 + 聊天模式整合方案 + 前後端任務卡 + Swagger YAML +
Postman JSON。

## 0. 高階總覽（Executive Summary）

目標：在既有商品搜尋模式基礎上，提供自然語言的聊天模式，並確保多組商品結果可以在聊天區完整顯示。

交付物：本文件（整合版）、Swagger YAML、Postman
JSON、前端與後端任務卡（可直接貼到 VS Code）。

## 1. 系統架構

Client (React + Tailwind)\
├─ ChatView（聊天模式）\
├─ SearchView（商品搜尋模式）\
├─ Shared UI：商品卡、過濾器、Toast、Loading、空狀態\
└─ API SDK：/src/api/searchClient.ts\
\
Server (Python Flask/FastAPI)\
├─ /api/search \# 關鍵字/條件查詢\
├─ /api/chat-search \# 自然語言 → 語義解析 → 商品檢索（支援群組回傳）\
├─ /api/upload-csv \# 管理者上傳商品資料\
├─ /api/version \# 版本\
├─ /api/healthz \# 健康檢查\
└─ core/ loaders \| preprocess \| embeddings \| index \| rankers\
\
Storage\
├─ VIEW_GOODS.csv / .parquet\
├─ 查詢日誌（可選）\
└─ 向量索引（可選 FAISS/HNSW）\
\
Ops\
├─ 前端：Netlify\
└─ 後端：Render

## 2. 資料模型與清洗

來源表 VIEW_GOODS 欄位：\
-
GoodIden（PK）、Name、Description、Price、SpecialOffer、Category、Tags、Goods_link1、Goodspic_link1、UpdatedAt\
清洗：全半形轉換、空白修剪、大小寫正規化、同義詞表、中文分詞/英文詞幹、產出
Tags。

## 3. API 摘要

\- POST /api/search：關鍵字/條件搜尋\
- POST /api/chat-search：聊天模式（支援 groups\[\] 與 items\[\]）\
- POST /api/upload-csv：上傳商品 CSV（需 Bearer Token）\
- GET /api/version：版本資訊\
- GET /api/healthz：健康檢查\
詳細 Schema 見附錄 A（Swagger）。

## 4. 聊天模式（Chat Mode）UX

\- 初始載入即為聊天模式，輸入自然語言需求。\
- 後端回傳 reply + groups（多組商品）或 items（單組商品）。\
- 前端以群組標題 + 商品卡清單方式渲染；若僅 items，則維持原行為。\
- 查無資料：顯示放寬條件建議與 related_queries。

## 5. 排序與商業權重

特價優先、熱賣權重、價差提示，相似商品推薦。

## 6. 錯誤處理、安全、部署

\- 錯誤碼：400/401/413/422/429/500；統一 ErrorResponse 格式。\
- 安全：上傳需 Bearer Token，節流保護；CORS 白名單。\
- 部署：前端 Netlify、後端 Render；版本回報 /api/version。

## 7. 測試與里程碑

\- 單元/整合/回歸/可用性測試。\
- M1：聊天模式 MVP（含多組顯示）；M2：語義強化；M3：商業化優化。

## 8. 任務卡（前端）：多組商品顯示

🎯 目的：當 /api/chat-search 回傳 groups\[\]
時，逐組渲染商品，避免只顯示第一組。\
修改檔：\
- frontend/src/components/ChatView.tsx\
- frontend/src/components/MessageBubble.tsx\
- frontend/src/components/ProductCard.tsx\
- frontend/src/api/searchClient.ts（型別）\
\
型別：\
export interface ChatGroup { category: string; items: ProductItem\[\];
}\
export interface ChatSearchResponse { reply: string; groups?:
ChatGroup\[\]; items?: ProductItem\[\]; related_queries?: string\[\]; }\
\
渲染範例（ChatView.tsx）:\
{response.groups\
? response.groups.map((group, idx) =\> (\
\<div key={idx} className=\"mt-4\"\>\
\<h4 className=\"font-semibold mb-2\"\>{idx + 1}.
{group.category}\</h4\>\
\<div className=\"grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
gap-4\"\>\
{group.items.map((item) =\> (\<ProductCard key={item.GoodIden}
product={item} /\>))}\
\</div\>\
\</div\>\
))\
: response.items?.map((item) =\> (\<ProductCard key={item.GoodIden}
product={item} /\>))\
}\
驗收：多組（餅乾/飲料/休閒）皆顯示，單組時維持原行為。

## 9. 任務卡（後端）：/api/chat-search 回傳多組商品

🎯 目的：讓後端可根據意圖與抽取的條件，輸出分組結果。\
修改檔：\
- backend/app.py（或 main.py / routers/chat.py）\
- backend/core/nlu.py（意圖/實體抽取）\
- backend/core/retriever.py（檢索）\
- backend/core/formatter.py（分組組裝）\
\
回傳格式：\
{\
\"reply\": \"為了讓您的假日聚餐更豐富多彩，我建議以下商品組合：\",\
\"groups\": \[\
{\"category\": \"餅乾類\", \"items\": \[ProductItem\...\]},\
{\"category\": \"飲料類\", \"items\": \[ProductItem\...\]},\
{\"category\": \"休閒食品類\", \"items\": \[ProductItem\...\]}\
\],\
\"related_queries\": \[\"其他建議\...\"\],\
\"traces\": {\"intent\":\"bundle_recommendation\",\"entities\":{\...}}\
}\
\
Pseudo-code：\
intent, entities = nlu.parse(req.message)\
buckets = plan_bundles(entities) \# 例如「餅乾/飲料/休閒」\
groups = \[\]\
for b in buckets:\
cand = retriever.search(category=b, entities=entities, top_k=5)\
groups.append({\"category\": b, \"items\": ranker.sort(cand)\[:5\]})\
reply = nlg.compose_bundle_reply(groups)\
return {\"reply\": reply, \"groups\": groups, \"related_queries\":
build_related(groups)}\
\
驗收：\
- 回傳 groups\[\] 至少 2 組且各有 items。\
- groups 與 items 結構符合 Swagger Schemas（Appendix A）。\
- 單組需求可回傳 items\[\]（向下相容）。

## 附錄 A：Swagger（OpenAPI 3.0）YAML

檔案下載：

SEARCH_Goods_openapi_v1.yaml（點此下載）:
sandbox:/mnt/data/SEARCH_Goods_openapi_v1.yaml

完整內文如下：

openapi: 3.0.3\
info:\
title: SEARCH_Goods API\
description: 商品查詢（哈通）--- 搜尋模式與聊天模式 API 規格\
version: \"1.0.0\"\
servers:\
- url: https://search-goods-api.onrender.com\
description: Render Production\
- url: http://localhost:8000\
description: Local Dev\
tags:\
- name: Search\
description: 關鍵字/條件商品查詢\
- name: Chat\
description: 聊天模式自然語言查詢\
- name: Admin\
description: 管理者功能（需 Bearer Token）\
- name: Meta\
description: 版本與健康檢查\
paths:\
/api/search:\
post:\
tags: \[Search\]\
summary: 商品搜尋（關鍵字/條件）\
requestBody:\
required: true\
content:\
application/json:\
schema:\
\$ref: \'#/components/schemas/SearchRequest\'\
examples:\
basic:\
summary: 基本查詢\
value:\
q: \"核桃 無調味\"\
filters:\
category: \[\"堅果\"\]\
price: {min: 200, max: 600}\
sort: \"offer_first\"\
page: 1\
page_size: 24\
responses:\
\"200\":\
description: 搜尋結果\
content:\
application/json:\
schema:\
\$ref: \'#/components/schemas/SearchResponse\'\
\"400\":\
\$ref: \'#/components/responses/BadRequest\'\
\"500\":\
\$ref: \'#/components/responses/ServerError\'\
/api/chat-search:\
post:\
tags: \[Chat\]\
summary: 聊天模式自然語言查詢\
requestBody:\
required: true\
content:\
application/json:\
schema:\
\$ref: \'#/components/schemas/ChatSearchRequest\'\
examples:\
example1:\
summary: 找 300 元內無調味核桃\
value:\
message: \"想找沒有加鹽的核桃，300元內有嗎？\"\
context: {locale: \"zh-TW\", currency: \"TWD\"}\
top_k: 10\
responses:\
\"200\":\
description: 對話回覆與商品結果\
content:\
application/json:\
schema:\
\$ref: \'#/components/schemas/ChatSearchResponse\'\
\"400\":\
\$ref: \'#/components/responses/BadRequest\'\
\"500\":\
\$ref: \'#/components/responses/ServerError\'\
/api/upload-csv:\
post:\
tags: \[Admin\]\
summary: 上傳商品資料 CSV（管理者）\
security:\
- bearerAuth: \[\]\
requestBody:\
required: true\
content:\
multipart/form-data:\
schema:\
type: object\
properties:\
file:\
type: string\
format: binary\
description: VIEW_GOODS.csv 檔案\
responses:\
\"200\":\
description: 上傳結果與新版本資訊\
content:\
application/json:\
schema:\
type: object\
properties:\
ok:\
type: boolean\
updated:\
type: integer\
version:\
type: string\
\"400\":\
\$ref: \'#/components/responses/BadRequest\'\
\"401\":\
\$ref: \'#/components/responses/Unauthorized\'\
\"422\":\
\$ref: \'#/components/responses/Unprocessable\'\
\"500\":\
\$ref: \'#/components/responses/ServerError\'\
/api/version:\
get:\
tags: \[Meta\]\
summary: 版本資訊\
responses:\
\"200\":\
description: 版本資訊\
content:\
application/json:\
schema:\
type: object\
properties:\
version:\
type: string\
data_updated_at:\
type: string\
format: date-time\
/api/healthz:\
get:\
tags: \[Meta\]\
summary: 健康檢查\
responses:\
\"200\":\
description: OK\
content:\
application/json:\
schema:\
type: object\
properties:\
status:\
type: string\
example: \"ok\"\
components:\
securitySchemes:\
bearerAuth:\
type: http\
scheme: bearer\
bearerFormat: JWT\
responses:\
BadRequest:\
description: 參數錯誤\
content:\
application/json:\
schema:\
\$ref: \'#/components/schemas/ErrorResponse\'\
Unauthorized:\
description: 未授權\
content:\
application/json:\
schema:\
\$ref: \'#/components/schemas/ErrorResponse\'\
Unprocessable:\
description: Schema 不符合或內容無效\
content:\
application/json:\
schema:\
\$ref: \'#/components/schemas/ErrorResponse\'\
ServerError:\
description: 伺服器錯誤\
content:\
application/json:\
schema:\
\$ref: \'#/components/schemas/ErrorResponse\'\
schemas:\
SearchRequest:\
type: object\
properties:\
q:\
type: string\
description: 查詢字串\
filters:\
type: object\
properties:\
category:\
type: array\
items: { type: string }\
price:\
type: object\
properties:\
min: { type: number }\
max: { type: number }\
sort:\
type: string\
enum: \[relevance, price_asc, price_desc, offer_first\]\
page:\
type: integer\
minimum: 1\
default: 1\
page_size:\
type: integer\
minimum: 1\
maximum: 100\
default: 24\
SearchResponse:\
type: object\
properties:\
total: { type: integer }\
page: { type: integer }\
page_size: { type: integer }\
items:\
type: array\
items:\
\$ref: \'#/components/schemas/ProductItem\'\
did_you_mean:\
type: array\
items: { type: string }\
debug:\
type: object\
properties:\
latency_ms: { type: number }\
ChatSearchRequest:\
type: object\
required: \[message\]\
properties:\
message:\
type: string\
description: 使用者自然語言輸入\
context:\
type: object\
properties:\
locale: { type: string, example: \"zh-TW\" }\
currency: { type: string, example: \"TWD\" }\
top_k:\
type: integer\
minimum: 1\
maximum: 50\
default: 10\
ChatSearchResponse:\
type: object\
properties:\
reply: { type: string }\
items:\
type: array\
items:\
\$ref: \'#/components/schemas/ProductItem\'\
related_queries:\
type: array\
items: { type: string }\
traces:\
type: object\
additionalProperties: true\
ProductItem:\
type: object\
properties:\
GoodIden: { type: string }\
Name: { type: string }\
Description: { type: string }\
Price: { type: number }\
SpecialOffer: { type: number, nullable: true }\
Goods_link1: { type: string, format: uri }\
Goodspic_link1: { type: string, format: uri }\
Highlights:\
type: array\
items: { type: string }\
Score: { type: number }\
ErrorResponse:\
type: object\
properties:\
error:\
type: object\
properties:\
code: { type: integer }\
message: { type: string }\
security: \[\]

## 附錄 B：Postman Collection JSON

檔案下載：

SEARCH_Goods_Postman_v1.json（點此下載）:
sandbox:/mnt/data/SEARCH_Goods_Postman_v1.json

完整內文如下：

{\
\"info\": {\
\"name\": \"SEARCH_Goods API Collection\",\
\"\_postman_id\": \"c5f1bb7e-0a1a-4f0a-bc2b-20251023072141\",\
\"description\": \"Postman collection for SEARCH_Goods 搜尋與聊天模式
API\",\
\"schema\":
\"https://schema.getpostman.com/json/collection/v2.1.0/collection.json\"\
},\
\"item\": \[\
{\
\"name\": \"Search - 商品搜尋\",\
\"request\": {\
\"method\": \"POST\",\
\"header\": \[\
{\
\"key\": \"Content-Type\",\
\"value\": \"application/json\"\
}\
\],\
\"url\": {\
\"raw\": \"{{baseUrl}}/api/search\",\
\"host\": \[\
\"{{baseUrl}}\"\
\],\
\"path\": \[\
\"api\",\
\"search\"\
\]\
},\
\"body\": {\
\"mode\": \"raw\",\
\"raw\": \"{\\n \\\"q\\\": \\\"核桃 無調味\\\",\\n \\\"filters\\\": {\\n
\\\"category\\\": \[\\n \\\"堅果\\\"\\n \],\\n \\\"price\\\": {\\n
\\\"min\\\": 200,\\n \\\"max\\\": 600\\n }\\n },\\n \\\"sort\\\":
\\\"offer_first\\\",\\n \\\"page\\\": 1,\\n \\\"page_size\\\": 24\\n}\"\
},\
\"description\": \"依關鍵字/條件查詢商品\"\
},\
\"response\": \[\]\
},\
{\
\"name\": \"Chat - 聊天模式查詢\",\
\"request\": {\
\"method\": \"POST\",\
\"header\": \[\
{\
\"key\": \"Content-Type\",\
\"value\": \"application/json\"\
}\
\],\
\"url\": {\
\"raw\": \"{{baseUrl}}/api/chat-search\",\
\"host\": \[\
\"{{baseUrl}}\"\
\],\
\"path\": \[\
\"api\",\
\"chat-search\"\
\]\
},\
\"body\": {\
\"mode\": \"raw\",\
\"raw\": \"{\\n \\\"message\\\":
\\\"想找沒有加鹽的核桃，300元內有嗎？\\\",\\n \\\"context\\\": {\\n
\\\"locale\\\": \\\"zh-TW\\\",\\n \\\"currency\\\": \\\"TWD\\\"\\n },\\n
\\\"top_k\\\": 10\\n}\"\
},\
\"description\": \"自然語言對話檢索商品並回覆摘要\"\
},\
\"response\": \[\]\
},\
{\
\"name\": \"Admin - 上傳 CSV\",\
\"request\": {\
\"method\": \"POST\",\
\"header\": \[\
{\
\"key\": \"Authorization\",\
\"value\": \"Bearer {{ADMIN_TOKEN}}\",\
\"type\": \"text\"\
}\
\],\
\"url\": {\
\"raw\": \"{{baseUrl}}/api/upload-csv\",\
\"host\": \[\
\"{{baseUrl}}\"\
\],\
\"path\": \[\
\"api\",\
\"upload-csv\"\
\]\
},\
\"body\": {\
\"mode\": \"formdata\",\
\"formdata\": \[\
{\
\"key\": \"file\",\
\"type\": \"file\",\
\"src\": \[\
\"/path/to/VIEW_GOODS.csv\"\
\]\
}\
\]\
},\
\"description\": \"管理者上傳最新商品 CSV，會觸發 schema
校驗與索引重建\"\
},\
\"response\": \[\]\
},\
{\
\"name\": \"Meta - 版本資訊\",\
\"request\": {\
\"method\": \"GET\",\
\"url\": {\
\"raw\": \"{{baseUrl}}/api/version\",\
\"host\": \[\
\"{{baseUrl}}\"\
\],\
\"path\": \[\
\"api\",\
\"version\"\
\]\
},\
\"description\": \"查詢目前 API 版本與資料更新時間\"\
},\
\"response\": \[\]\
},\
{\
\"name\": \"Meta - 健康檢查\",\
\"request\": {\
\"method\": \"GET\",\
\"url\": {\
\"raw\": \"{{baseUrl}}/api/healthz\",\
\"host\": \[\
\"{{baseUrl}}\"\
\],\
\"path\": \[\
\"api\",\
\"healthz\"\
\]\
},\
\"description\": \"健康檢查（K8s/Render 用）\"\
},\
\"response\": \[\]\
}\
\],\
\"variable\": \[\
{\
\"key\": \"baseUrl\",\
\"value\": \"https://search-goods-api.onrender.com\"\
},\
{\
\"key\": \"ADMIN_TOKEN\",\
\"value\": \"YOUR_ADMIN_TOKEN\"\
}\
\]\
}

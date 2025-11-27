# CompanyResponseFormatter 測試指南

本指南說明如何測試 `company_response_formatter.py` 模組。

---

## 📋 測試環境

### 系統需求
- Python 3.7+
- 相關套件: `typing`, `urllib.parse`
- 選配: `pytest` (用於自動化測試)

### 檔案結構
```
backend/
├── company_response_formatter.py       # 主程式
├── test_formatter_interactive.py       # 互動式測試工具
└── tests/
    └── test_company_response_formatter.py  # 單元測試
```

---

## 🧪 測試方法

### 方法 1: 互動式測試 (推薦新手)

最簡單的測試方式，提供視覺化選單：

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend
python3 test_formatter_interactive.py
```

**功能:**
- 📞 測試聯絡資訊格式化
- 🛠️ 測試服務項目格式化
- 🏢 測試公司介紹格式化
- ⏰ 測試營業時間格式化
- ❓ 測試 FAQ 格式化
- 🎉 測試促銷活動格式化
- 🔧 測試單例模式
- 🔗 測試 URL 編碼

---

### 方法 2: 單元測試 (推薦開發者)

使用 pytest 執行完整的單元測試：

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend

# 方式 A: 使用 pytest (需先安裝)
pip3 install pytest
pytest tests/test_company_response_formatter.py -v

# 方式 B: 直接執行測試檔案
python3 tests/test_company_response_formatter.py
```

**測試覆蓋:**
- ✅ 基本功能測試
- ✅ 邊界條件測試 (空資料、空字串等)
- ✅ Rich Content 結構驗證
- ✅ Google Maps URL 生成
- ✅ 單例模式驗證
- ✅ 錯誤處理

---

### 方法 3: 內建測試

執行檔案內建的測試程式：

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend
python3 company_response_formatter.py
```

這會自動測試所有格式化功能，並顯示結果。

---

### 方法 4: Python 互動式測試

手動逐步測試，適合除錯：

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend
python3
```

然後在 Python 提示符執行：

```python
from company_response_formatter import get_company_response_formatter

# 建立格式化器
formatter = get_company_response_formatter()

# 測試聯絡資訊
contacts = {
    'company_phone_local': '04-27062295',
    'address': '台中市河南路二段 262 號'
}
result = formatter.format_contact_info(contacts)
print(result['text'])

# 測試空資料
empty_result = formatter.format_contact_info({})
print(empty_result['text'])

# 測試單例模式
formatter2 = get_company_response_formatter()
print('單例模式:', formatter is formatter2)  # 應該是 True

# 離開
exit()
```

---

## 📊 測試檢查清單

### ✅ 功能測試
- [ ] 聯絡資訊格式化 (完整資料)
- [ ] 聯絡資訊格式化 (部分資料)
- [ ] 聯絡資訊格式化 (空資料)
- [ ] 服務項目格式化
- [ ] 公司介紹格式化
- [ ] 營業時間格式化
- [ ] FAQ 格式化 (單一)
- [ ] FAQ 格式化 (列表)
- [ ] 促銷活動格式化

### ✅ 結構測試
- [ ] Rich Content 包含 `type` 欄位
- [ ] Rich Content 包含 `items` 陣列
- [ ] 每個 item 包含必要欄位 (type, label, value, icon)
- [ ] Google Maps URL 正確生成
- [ ] 電話號碼 tel: 連結正確

### ✅ 邊界條件
- [ ] 空字典處理
- [ ] None 值處理
- [ ] 缺少 key 的處理
- [ ] 超長文字截斷

### ✅ 設計模式
- [ ] 單例模式正確實作
- [ ] 多次呼叫返回同一實例

---

## 🐛 常見問題

### 問題 1: 找不到模組
```
ModuleNotFoundError: No module named 'company_response_formatter'
```

**解決方法:**
確保在 `backend/` 目錄下執行測試。

---

### 問題 2: Emoji 顯示亂碼
```
� 或 \ufffd
```

**解決方法:**
- 檢查終端機編碼設定 (應為 UTF-8)
- macOS: 終端機預設應該支援
- 確認檔案已修正 (本地版本已修正)

---

### 問題 3: pytest 未安裝
```
ModuleNotFoundError: No module named 'pytest'
```

**解決方法:**
```bash
pip3 install pytest
```

或直接執行不需要 pytest 的測試：
```bash
python3 tests/test_company_response_formatter.py
```

---

## 📈 測試結果範例

### 成功輸出範例

```
============================================================
測試 CompanyResponseFormatter
============================================================

============================================================
📝 測試主題: 聯絡資訊
============================================================
📞 傳啟資訊聯絡方式

🏢 公司電話：04-27062295
📞 客服專線：04-26062295
📍 公司地址：台中市河南路二段 262 號 3 樓之 11
🌐 官方網站：https://www.myqr.com.tw
⏰ 服務時間：週一至週五 09:00-18:00

🔗 了解更多：https://www.myqr.com.tw
🎥 公司介紹影片：https://youtu.be/E8RfyZoFixY

您可以透過以上方式與我們聯繫，或直接訪問官網了解更多資訊！
```

---

## 🚀 快速測試指令

複製貼上即可執行：

```bash
# 切換到 backend 目錄
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend

# 執行互動式測試 (最簡單)
python3 test_formatter_interactive.py

# 或執行內建測試
python3 company_response_formatter.py

# 或執行單元測試 (如果已安裝 pytest)
pytest tests/test_company_response_formatter.py -v

# 或不使用 pytest 執行單元測試
python3 tests/test_company_response_formatter.py
```

---

## 📝 補充說明

### 與 GitHub 版本的差異

本地版本已修正以下問題：
1. ✅ Emoji 顯示錯誤 (第 388 行)
2. ✅ 重複 emoji 問題 (第 410 行)
3. ✅ import 語句優化 (移至模組頂部)

測試時應該不會看到亂碼字符。

---

## 📞 支援

如有問題，請檢查：
1. Python 版本 (需 3.7+)
2. 檔案編碼 (應為 UTF-8)
3. 工作目錄 (應在 backend/)
4. 相依檔案是否存在

---

**最後更新:** 2025年11月24日

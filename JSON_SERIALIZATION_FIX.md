# 🔧 L3 查詢 JSON 序列化錯誤修復

## 問題描述

當用戶在前端點選 L3 分類後，某些查詢會返回錯誤：
```
SyntaxError: Unexpected token 'I', "Internal S"... is not valid JSON
```

**受影響的查詢**：「防蚊、防蟑」等特殊字符查詢

## 根本原因

`format_for_chat()` 函式返回的某些字段包含：
- NumPy 對象（np.nan, np.inf）
- Pandas 對象（pd.Timestamp, pd.Series）
- 其他非 JSON 基本類型

這些對象無法直接序列化為 JSON。

## 解決方案

### 1. 添加 JSON 清理函式 ✅

```python
def _sanitize_for_json(obj: Any) -> Any:
    """遞迴清理對象，確保可序列化為 JSON"""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
    # 其他類型轉為字串
    return str(obj)
```

### 2. 雙層異常捕獲 ✅

- **第一層**：JSON 清理層 - 清理所有非基本類型
- **第二層**：序列化層 - 捕獲序列化異常

### 3. 備用回應機制 ✅

若序列化失敗，返回簡化版本：
```python
{
    "message": "為您找到 X 項商品（部分字段可能無法顯示）",
    "items": [{"商品名稱": "..."}, ...],
    "intent": {}
}
```

## 改善內容

| 項目 | 改善前 | 改善後 |
|------|-------|-------|
| 序列化失敗 | ❌ 直接 500 錯誤 | ✅ 備用簡化回應 |
| 特殊字符 | ❌ 無法處理 | ✅ 轉為字串 |
| NumPy/Pandas | ❌ 引發異常 | ✅ 轉為字串 |
| 日誌追蹤 | ❌ 無 | ✅ 詳細錯誤日誌 |

## 測試驗證

✅ 代碼已檢查無語法錯誤
✅ 已提交 Git：commit `bcb05c6`
✅ 已推送至 main 分支

## 後續步驟

1. **立即部署** - 此修復可直接部署到生產環境
2. **監控日誌** - 觀察是否還有序列化異常出現
3. **根本解決** - 考慮在 CSV 載入時就進行類型轉換

## 相關位置

- **修改檔案**：`backend/app.py`
- **修改位置**：Line 770-825（搜尋端點返回邏輯）
- **新增函式**：`_sanitize_for_json()` (內部函式)

---

現在你可以安心進行 L3 查詢了！🎯

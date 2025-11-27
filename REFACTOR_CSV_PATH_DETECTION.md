# 📁 CSV 路徑偵測重構方案

**問題識別日期**: 2025年11月12日  
**優先級**: 🟡 中 (維護性改善)  
**影響範圍**: backend/app.py, backend/goods_search_service.py, backend/repair_search_service.py

---

## 🔴 問題分析

### 現況

目前有 **3 處重複的路徑偵測邏輯**：

| 位置 | 函數名稱 | 環境變數 | 檔案名稱 |
|------|---------|---------|---------|
| `app.py` (Line 117) | `_get_csv_path()` | `DATA_PATH` | `VIEW_GOODS_enhanced.csv` |
| `goods_search_service.py` (Line 65) | `_get_csv_path()` | `DATA_PATH` | `VIEW_GOODS_enhanced.csv` |
| `repair_search_service.py` (Line 68) | `_get_repair_csv_path()` | `REPAIR_DATA_PATH` | `集合式住宅報修資料.csv` |

### 重複邏輯

```python
# 三處都有幾乎相同的邏輯：
def _get_xxx_csv_path():
    """自動檢測並返回正確的 CSV 文件路徑"""
    # 1. 檢查環境變數
    env_path = os.getenv("DATA_PATH")  # 或 REPAIR_DATA_PATH
    if env_path:
        return Path(env_path)
    
    # 2. 檢查 Render 環境
    render_path = Path("/opt/render/project/src/data/xxx.csv")
    if render_path.exists():
        return render_path
    
    # 3. 默認本地開發路徑
    return ROOT / "data" / "xxx.csv"
```

### 風險分析

| 風險類型 | 描述 | 影響 |
|---------|------|------|
| **維護困難** | 修改一處需要同步修改三處 | 🔴 高 |
| **行為差異** | 三處邏輯可能因疏忽而不一致 | 🟠 中 |
| **測試複雜** | 需要測試三處不同的函數 | 🟡 中 |
| **程式碼重複** | 違反 DRY (Don't Repeat Yourself) 原則 | 🟡 中 |

---

## ✅ 建議方案

### 方案 A: 集中式路徑管理器（推薦）⭐

建立專門的 `path_manager.py` 模組，集中管理所有資料檔案路徑。

#### 實作步驟

**1. 建立新模組 `backend/path_manager.py`**

```python
# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 路徑管理器
================================================================================

檔案名稱: path_manager.py
建立日期: 2025年11月12日

功能描述:
    集中管理所有資料檔案的路徑偵測邏輯，避免重複代碼

核心功能:
    - get_data_path(env_var, filename) - 通用路徑偵測
    - GOODS_DATA_PATH - 商品資料路徑
    - REPAIR_DATA_PATH - 維修資料路徑
================================================================================
"""
from pathlib import Path
import os
from typing import Optional

# 專案根目錄
ROOT = Path(__file__).resolve().parents[1]


def get_data_path(
    env_var: str,
    default_filename: str,
    render_path: Optional[str] = None
) -> Path:
    """
    通用的資料檔案路徑偵測函數
    
    偵測順序:
    1. 環境變數指定的路徑
    2. Render 環境的標準路徑
    3. 本地開發環境的默認路徑
    
    Args:
        env_var: 環境變數名稱 (例: "DATA_PATH", "REPAIR_DATA_PATH")
        default_filename: 默認檔案名稱 (例: "VIEW_GOODS_enhanced.csv")
        render_path: Render 環境的完整路徑 (可選)
    
    Returns:
        Path: 偵測到的檔案路徑
    
    Examples:
        >>> get_data_path("DATA_PATH", "VIEW_GOODS_enhanced.csv")
        PosixPath('/path/to/data/VIEW_GOODS_enhanced.csv')
    """
    # 1. 優先使用環境變數
    env_path = os.getenv(env_var)
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
        # 如果環境變數設定的路徑不存在，記錄警告但繼續偵測
        import logging
        logging.warning(f"{env_var}={env_path} 不存在，使用默認偵測邏輯")
    
    # 2. 檢查 Render 環境路徑
    if render_path:
        render_full_path = Path(render_path)
        if render_full_path.exists():
            return render_full_path
    
    # 3. 默認本地開發路徑
    default_path = ROOT / "data" / default_filename
    return default_path


# ============================================================================
# 預定義的資料路徑
# ============================================================================

# 商品資料路徑
GOODS_DATA_PATH = get_data_path(
    env_var="DATA_PATH",
    default_filename="VIEW_GOODS_enhanced.csv",
    render_path="/opt/render/project/src/data/VIEW_GOODS_enhanced.csv"
)

# 維修資料路徑
REPAIR_DATA_PATH = get_data_path(
    env_var="REPAIR_DATA_PATH",
    default_filename="集合式住宅報修資料.csv",
    render_path="/opt/render/project/src/data/集合式住宅報修資料.csv"
)


# ============================================================================
# 工具函數
# ============================================================================

def get_all_data_paths() -> dict:
    """
    返回所有資料路徑的字典（用於診斷）
    
    Returns:
        dict: 包含所有資料路徑及其狀態
    """
    return {
        "goods_data": {
            "path": str(GOODS_DATA_PATH),
            "exists": GOODS_DATA_PATH.exists(),
            "size": GOODS_DATA_PATH.stat().st_size if GOODS_DATA_PATH.exists() else 0,
            "env_var": "DATA_PATH",
            "env_value": os.getenv("DATA_PATH")
        },
        "repair_data": {
            "path": str(REPAIR_DATA_PATH),
            "exists": REPAIR_DATA_PATH.exists(),
            "size": REPAIR_DATA_PATH.stat().st_size if REPAIR_DATA_PATH.exists() else 0,
            "env_var": "REPAIR_DATA_PATH",
            "env_value": os.getenv("REPAIR_DATA_PATH")
        }
    }


def validate_data_paths() -> bool:
    """
    驗證所有資料路徑是否有效
    
    Returns:
        bool: 如果所有路徑都存在且可讀則返回 True
    """
    paths = [GOODS_DATA_PATH, REPAIR_DATA_PATH]
    all_valid = True
    
    for path in paths:
        if not path.exists():
            import logging
            logging.error(f"資料檔案不存在: {path}")
            all_valid = False
        elif not os.access(path, os.R_OK):
            import logging
            logging.error(f"資料檔案無法讀取: {path}")
            all_valid = False
    
    return all_valid


if __name__ == "__main__":
    # 測試與診斷
    import json
    print(json.dumps(get_all_data_paths(), indent=2, ensure_ascii=False))
```

---

**2. 修改 `backend/app.py`**

```python
# 修改前 (Line 117-132)
def _get_csv_path():
    """自動檢測並返回正確的 CSV 文件路徑"""
    env_path = os.getenv("DATA_PATH")
    if env_path:
        return Path(env_path)
    
    render_path = Path("/opt/render/project/src/data/VIEW_GOODS_enhanced.csv")
    if render_path.exists():
        return render_path
    
    return ROOT / "data" / "VIEW_GOODS_enhanced.csv"

DATA_PATH = _get_csv_path()

# 修改後
from path_manager import GOODS_DATA_PATH as DATA_PATH
```

**簡化**: 15 行 → 1 行 ✅

---

**3. 修改 `backend/goods_search_service.py`**

```python
# 修改前 (Line 65-80)
def _get_csv_path():
    """自動檢測並返回正確的 CSV 文件路徑"""
    env_path = os.getenv("DATA_PATH")
    if env_path:
        return Path(env_path)
    
    render_path = Path("/opt/render/project/src/data/VIEW_GOODS_enhanced.csv")
    if render_path.exists():
        return render_path
    
    return ROOT / "data" / "VIEW_GOODS_enhanced.csv"

DEFAULT_DATA_PATH = _get_csv_path()

# 修改後
from path_manager import GOODS_DATA_PATH as DEFAULT_DATA_PATH
```

**簡化**: 15 行 → 1 行 ✅

---

**4. 修改 `backend/repair_search_service.py`**

```python
# 修改前 (Line 68-83)
def _get_repair_csv_path() -> Path:
    """自動檢測並返回正確的維修資料 CSV 路徑"""
    env_path = os.getenv("REPAIR_DATA_PATH")
    if env_path:
        return Path(env_path)
    
    render_path = Path("/opt/render/project/src/data/集合式住宅報修資料.csv")
    if render_path.exists():
        return render_path
    
    return ROOT / "data" / "集合式住宅報修資料.csv"

DEFAULT_REPAIR_CSV_PATH = _get_repair_csv_path()

# 修改後
from path_manager import REPAIR_DATA_PATH as DEFAULT_REPAIR_CSV_PATH
```

**簡化**: 15 行 → 1 行 ✅

---

**5. 新增測試 `backend/tests/test_path_manager.py`**

```python
# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 路徑管理器測試
================================================================================
"""
import pytest
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from path_manager import (
    get_data_path,
    GOODS_DATA_PATH,
    REPAIR_DATA_PATH,
    get_all_data_paths,
    validate_data_paths
)


class TestGetDataPath:
    """測試通用路徑偵測函數"""
    
    def test_env_var_priority(self, monkeypatch):
        """測試環境變數優先級"""
        test_path = "/tmp/test_data.csv"
        Path(test_path).touch()  # 建立測試檔案
        
        monkeypatch.setenv("TEST_PATH", test_path)
        
        result = get_data_path("TEST_PATH", "default.csv")
        assert result == Path(test_path)
        
        # 清理
        os.remove(test_path)
    
    def test_default_path_fallback(self):
        """測試默認路徑降級"""
        result = get_data_path(
            "NON_EXISTENT_VAR",
            "test.csv"
        )
        
        assert result.name == "test.csv"
        assert "data" in str(result)
    
    def test_render_path_detection(self):
        """測試 Render 路徑偵測"""
        # 模擬 Render 環境
        render_path = "/opt/render/project/src/data/test.csv"
        
        result = get_data_path(
            "NON_EXISTENT_VAR",
            "test.csv",
            render_path=render_path
        )
        
        # 如果 Render 路徑不存在，應該降級到默認路徑
        if not Path(render_path).exists():
            assert "data/test.csv" in str(result)


class TestPredefinedPaths:
    """測試預定義的路徑"""
    
    def test_goods_data_path_defined(self):
        """測試商品資料路徑已定義"""
        assert GOODS_DATA_PATH is not None
        assert isinstance(GOODS_DATA_PATH, Path)
        assert "VIEW_GOODS_enhanced.csv" in str(GOODS_DATA_PATH)
    
    def test_repair_data_path_defined(self):
        """測試維修資料路徑已定義"""
        assert REPAIR_DATA_PATH is not None
        assert isinstance(REPAIR_DATA_PATH, Path)
        assert "集合式住宅報修資料.csv" in str(REPAIR_DATA_PATH)


class TestUtilityFunctions:
    """測試工具函數"""
    
    def test_get_all_data_paths(self):
        """測試取得所有路徑"""
        paths = get_all_data_paths()
        
        assert "goods_data" in paths
        assert "repair_data" in paths
        assert "path" in paths["goods_data"]
        assert "exists" in paths["goods_data"]
    
    def test_validate_data_paths(self):
        """測試路徑驗證"""
        result = validate_data_paths()
        
        # 結果應該是布林值
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

#### 優點

| 優點 | 說明 |
|------|------|
| ✅ **單一職責** | 路徑邏輯集中在一個模組 |
| ✅ **易於維護** | 只需修改一處即可影響所有使用方 |
| ✅ **可測試性** | 獨立模組易於單元測試 |
| ✅ **可擴展性** | 未來新增其他資料源只需添加一行 |
| ✅ **診斷友善** | `get_all_data_paths()` 方便排查問題 |
| ✅ **向後兼容** | 不改變現有的變數名稱 |

#### 缺點

| 缺點 | 說明 | 緩解措施 |
|------|------|---------|
| ⚠️ **導入順序** | 需要在其他模組之前導入 | 已在設計中考慮，使用頂層導入 |
| ⚠️ **循環依賴** | 可能與其他模組產生循環依賴 | `path_manager.py` 不依賴任何業務邏輯模組 |

---

### 方案 B: 配置檔案方案

使用 `config.py` 統一管理配置，包括路徑。

#### 實作

```python
# backend/config.py
class Config:
    GOODS_DATA_PATH = get_data_path("DATA_PATH", "VIEW_GOODS_enhanced.csv")
    REPAIR_DATA_PATH = get_data_path("REPAIR_DATA_PATH", "集合式住宅報修資料.csv")
    # ... 其他配置
```

**優點**: 統一配置管理  
**缺點**: 配置檔案可能變得過於龐大

---

### 方案 C: 保持現狀，添加文件說明

不修改代碼，僅在文件中明確說明需要同步修改的位置。

**優點**: 零風險  
**缺點**: 不解決根本問題，維護負擔依然存在

---

## 🎯 推薦執行計畫

### 階段 1: 準備階段 (30分鐘)

- [ ] 建立 `backend/path_manager.py`
- [ ] 建立 `backend/tests/test_path_manager.py`
- [ ] 執行測試確保邏輯正確

### 階段 2: 重構階段 (20分鐘)

- [ ] 修改 `backend/app.py`
- [ ] 修改 `backend/goods_search_service.py`
- [ ] 修改 `backend/repair_search_service.py`

### 階段 3: 驗證階段 (30分鐘)

- [ ] 執行完整測試套件 `pytest`
- [ ] 本地開發環境驗證
- [ ] 模擬 Render 環境驗證
- [ ] 檢查所有環境變數路徑

### 階段 4: 部署階段 (10分鐘)

- [ ] 提交代碼
- [ ] CI/CD 驗證
- [ ] 部署到 Render
- [ ] 生產環境健康檢查

**預估總時間**: 90 分鐘

---

## 📝 遷移檢查清單

### 修改前確認

- [ ] 備份目前的程式碼
- [ ] 記錄所有使用 `DATA_PATH` 的位置
- [ ] 記錄所有使用 `DEFAULT_DATA_PATH` 的位置
- [ ] 記錄所有使用 `DEFAULT_REPAIR_CSV_PATH` 的位置

### 修改後確認

- [ ] 所有測試通過 (`pytest -v`)
- [ ] 端到端測試通過 (`npm run test:e2e`)
- [ ] 健康檢查端點返回正確路徑資訊
- [ ] 本地環境能正確載入資料
- [ ] Render 環境能正確載入資料

---

## 🔍 影響分析

### 受影響的文件

| 文件 | 影響類型 | 修改行數 | 風險 |
|------|---------|---------|------|
| `app.py` | 簡化導入 | -15, +1 | 🟢 低 |
| `goods_search_service.py` | 簡化導入 | -15, +1 | 🟢 低 |
| `repair_search_service.py` | 簡化導入 | -15, +1 | 🟢 低 |
| **新增**: `path_manager.py` | 新模組 | +150 | 🟢 低 |
| **新增**: `tests/test_path_manager.py` | 新測試 | +100 | 🟢 低 |

**總計**: -45 行重複代碼, +251 行新代碼 (含測試)

### 向後兼容性

✅ **完全兼容** - 變數名稱保持不變：
- `DATA_PATH` (app.py)
- `DEFAULT_DATA_PATH` (goods_search_service.py)
- `DEFAULT_REPAIR_CSV_PATH` (repair_search_service.py)

---

## 🚀 其他改進建議

### 1. 添加路徑驗證中間件

```python
# backend/app.py
@app.on_event("startup")
async def validate_paths_on_startup():
    """啟動時驗證所有資料路徑"""
    from path_manager import validate_data_paths
    if not validate_data_paths():
        logger.error("資料路徑驗證失敗，部分功能可能無法使用")
```

### 2. 健康檢查端點增強

```python
@app.get("/health")
def health_check():
    from path_manager import get_all_data_paths
    return {
        "status": "ok",
        "data_paths": get_all_data_paths(),  # 詳細路徑資訊
        # ... 其他健康狀態
    }
```

### 3. 環境變數文件更新

在 `.env.example` 中添加說明：

```bash
# 資料檔案路徑（可選）
# 如果不設定，系統會自動偵測 Render 或本地開發環境的默認路徑
DATA_PATH=/path/to/VIEW_GOODS_enhanced.csv
REPAIR_DATA_PATH=/path/to/集合式住宅報修資料.csv
```

---

## 📚 相關文件

- [DRY 原則](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)
- [Python Path 最佳實踐](https://docs.python.org/3/library/pathlib.html)
- [環境變數管理](https://12factor.net/config)

---

## 👥 負責人與審核

| 角色 | 姓名 | 職責 |
|------|------|------|
| 提議人 | GitHub Copilot | 問題分析與方案設計 |
| 審核人 | ______________ | 代碼審核 |
| 測試人 | ______________ | 測試驗證 |
| 部署人 | ______________ | 生產部署 |

---

**建立日期**: 2025年11月12日  
**預計完成**: 2025年11月__日  
**狀態**: 📋 待審核

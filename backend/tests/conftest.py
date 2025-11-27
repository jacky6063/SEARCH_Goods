# backend/tests/conftest.py
"""pytest 配置：當 CI 沒有 OPENAI_API_KEY 時，自動略過標記為 'llm' 的測試。"""

import os
import pytest

# 🔧 全局啟用維修服務（必須在任何導入之前）
os.environ["ENABLE_REPAIR_SERVICE"] = "True"


def pytest_configure(config):
    """註冊自訂 pytest 標記，避免 "Unknown pytest.mark" 警告。"""
    config.addinivalue_line(
        "markers", "llm: mark test as requiring OpenAI API key (LLM functionality)"
    )


def pytest_collection_modifyitems(config, items):
    """
    當 OPENAI_API_KEY 未設置或為空時，自動略過所有包含 'llm' 標記的測試。
    這樣 CI 環境可以在沒有 API 金鑰時成功運行。
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    # 檢查是否有有效的 API 金鑰
    has_valid_key = api_key and not api_key.lower().startswith("dummy")
    
    if not has_valid_key:
        skip_llm = pytest.mark.skip(reason="Skipping LLM tests: OPENAI_API_KEY not set in CI")
        for item in items:
            # 檢查測試函式是否標記為 llm 或名稱包含 llm
            if "llm" in item.keywords or "llm" in getattr(item, 'name', '').lower():
                item.add_marker(skip_llm)
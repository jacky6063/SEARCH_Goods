#!/usr/bin/env python3
"""
本地開發環境診斷工具
快速檢查所有常見問題
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_status(condition, success_msg, fail_msg):
    if condition:
        print(f"✅ {success_msg}")
        return True
    else:
        print(f"❌ {fail_msg}")
        return False


def main():
    print("🔧 SEARCH_Goods 本地開發環境診斷")
    
    all_good = True
    
    # 1. 檢查目錄結構
    print_header("1. 目錄結構檢查")
    
    backend_app = Path("backend/app.py")
    all_good &= check_status(
        backend_app.exists(),
        "backend/app.py 存在",
        "backend/app.py 不存在 - 請確認在專案根目錄執行"
    )
    
    frontend_html = Path("frontend/index.html")
    all_good &= check_status(
        frontend_html.exists(),
        "frontend/index.html 存在",
        "frontend/index.html 不存在"
    )
    
    env_file = Path(".env")
    env_exists = env_file.exists()
    all_good &= check_status(
        env_exists,
        ".env 檔案存在",
        ".env 檔案不存在 - 請從 .env.example 複製並填入真實憑證"
    )
    
    # 2. 檢查 Python 環境
    print_header("2. Python 環境檢查")
    
    python_version = sys.version.split()[0]
    version_parts = [int(x) for x in python_version.split('.')]
    python_ok = version_parts[0] >= 3 and version_parts[1] >= 9
    
    all_good &= check_status(
        python_ok,
        f"Python 版本: {python_version} (符合需求 >= 3.9)",
        f"Python 版本: {python_version} (需要 >= 3.9)"
    )
    
    venv_path = Path("backend/.venv")
    venv_exists = venv_path.exists()
    all_good &= check_status(
        venv_exists,
        "虛擬環境存在: backend/.venv",
        "虛擬環境不存在 - 執行: cd backend && python3 -m venv .venv"
    )
    
    # 3. 檢查必要套件
    print_header("3. Python 套件檢查")
    
    packages = {
        'fastapi': 'FastAPI',
        'supabase': 'Supabase',
        'openai': 'OpenAI',
        'uvicorn': 'Uvicorn',
        'pandas': 'Pandas',
    }
    
    for package, name in packages.items():
        try:
            __import__(package)
            check_status(True, f"{name} 已安裝", "")
        except ImportError:
            all_good &= check_status(
                False,
                "",
                f"{name} 未安裝 - 執行: pip install {package}"
            )
    
    # 4. 檢查環境變數
    print_header("4. 環境變數檢查")
    
    if env_exists:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = {
            'SUPABASE_URL': 'Supabase URL',
            'SUPABASE_KEY': 'Supabase Anon Key',
            'SUPABASE_SERVICE_KEY': 'Supabase Service Key',
        }
        
        for var, name in required_vars.items():
            value = os.getenv(var)
            has_value = value is not None and value != ""
            is_placeholder = value and ('your-project-id' in value or 'YOUR_' in value)
            
            if has_value and not is_placeholder:
                preview = value[:30] + "..." if len(value) > 30 else value
                check_status(True, f"{name}: {preview}", "")
            elif is_placeholder:
                all_good &= check_status(
                    False,
                    "",
                    f"{name} 使用佔位符 - 請填入真實憑證"
                )
            else:
                all_good &= check_status(
                    False,
                    "",
                    f"{name} 未設定"
                )
    else:
        print("⚠️  跳過環境變數檢查 (.env 不存在)")
    
    # 5. 檢查 Port 狀態
    print_header("5. Port 狀態檢查")
    
    def check_port(port):
        try:
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() != ""
        except Exception:
            return False
    
    port_8000_used = check_port(8000)
    check_status(
        not port_8000_used,
        "Port 8000 可用 (後端)",
        "Port 8000 被佔用 - 執行: lsof -ti:8000 | xargs kill -9"
    )
    
    port_5173_used = check_port(5173)
    check_status(
        not port_5173_used,
        "Port 5173 可用 (前端)",
        "Port 5173 被佔用 - 執行: lsof -ti:5173 | xargs kill -9"
    )
    
    # 6. 檢查 Import 路徑
    print_header("6. Python Import 檢查")
    
    if venv_exists:
        try:
            # 模擬從 backend 目錄 import
            old_path = sys.path.copy()
            backend_path = str(Path("backend").resolve())
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)
            
            try:
                from chat_logging import start_session
                check_status(True, "chat_logging 可正常 import", "")
            except ImportError as e:
                all_good &= check_status(False, "", f"chat_logging import 失敗: {e}")
            
            try:
                from chat_logging_bridge import ChatLoggingBridge
                check_status(True, "ChatLoggingBridge 可正常 import", "")
            except ImportError as e:
                all_good &= check_status(False, "", f"ChatLoggingBridge import 失敗: {e}")
            
            sys.path = old_path
            
        except Exception as e:
            all_good &= check_status(False, "", f"Import 測試失敗: {e}")
    else:
        print("⚠️  跳過 Import 檢查 (虛擬環境不存在)")
    
    # 總結
    print_header("診斷結果")
    
    if all_good:
        print("🎉 所有檢查通過!環境設定正確。")
        print("\n可以開始開發:")
        print("  ./start_local_dev.sh")
        print("\n或手動啟動:")
        print("  cd backend")
        print("  source .venv/bin/activate")
        print("  uvicorn app:app --reload --host 0.0.0.0 --port 8000")
        return 0
    else:
        print("⚠️  發現問題,請根據上方提示修正。")
        print("\n完整排除指南:")
        print("  docs/LOCAL_DEV_TROUBLESHOOTING.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())

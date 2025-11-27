#!/usr/bin/env python3
"""
測試 Humans role 功能
驗證新格式（role='Humans'）和舊格式（llm + 前綴）的相容性
"""

import sys
import os
from pathlib import Path

# 加入 backend 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def load_env():
    """載入環境變數"""
    env_file = backend_dir / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ[key.strip()] = value.strip()

def test_supabase_connection():
    """測試 Supabase 連線"""
    print("🔍 測試 Supabase 連線...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    if not supabase_url:
        print("❌ 未設定 SUPABASE_URL")
        print("📝 請在 .env 檔案加入 Supabase 設定")
        return False
    
    try:
        from supabase_client import get_supabase_client
        
        client = get_supabase_client()
        result = client.table('chat_messages').select('role', count='exact').limit(1).execute()
        print(f"✅ Supabase 連線成功")
        print(f"📊 chat_messages 資料表存在")
        return True
    except Exception as e:
        print(f"❌ Supabase 連線失敗: {e}")
        return False

def test_humans_role_support():
    """測試資料庫是否支援 Humans role"""
    print("\n🔍 測試資料庫是否支援 'Humans' role...")
    
    use_humans = os.getenv('USE_HUMANS_ROLE', 'True').lower() == 'true'
    print(f"📌 USE_HUMANS_ROLE 設定: {use_humans}")
    
    if not use_humans:
        print("⚠️  USE_HUMANS_ROLE=False，將使用舊格式（llm + 前綴）")
        return 'fallback'
    
    try:
        from supabase_client import get_supabase_client
        
        client = get_supabase_client(prefer_service_role=True)
        
        # 嘗試插入測試訊息
        test_data = {
            'session_id': 'test-humans-role-' + os.urandom(4).hex(),
            'role': 'Humans',
            'content': '測試 Humans role',
            'source_module': 'test'
        }
        
        result = client.table('chat_messages').insert(test_data).execute()
        
        if result.data:
            msg_id = result.data[0].get('message_id')
            print(f"✅ 資料庫支援 'Humans' role")
            print(f"📝 測試訊息 ID: {msg_id}")
            
            # 刪除測試訊息
            client.table('chat_messages').delete().eq('message_id', msg_id).execute()
            print(f"🗑️  測試訊息已刪除")
            return 'supported'
        else:
            print("❌ 插入失敗")
            return 'error'
            
    except Exception as e:
        error_msg = str(e)
        if 'invalid input value for enum message_role' in error_msg:
            print(f"❌ 資料庫不支援 'Humans' role")
            print(f"📋 需要執行 migration:")
            print(f"   ALTER TYPE message_role ADD VALUE IF NOT EXISTS 'Humans';")
            return 'not_supported'
        else:
            print(f"❌ 測試失敗: {e}")
            return 'error'

def show_migration_guide():
    """顯示 migration 指南"""
    print("\n" + "="*60)
    print("📚 執行 Migration 指南")
    print("="*60)
    
    supabase_url = os.getenv('SUPABASE_URL', 'https://your-project.supabase.co')
    
    print("\n方法1 - Supabase Dashboard（推薦）:")
    print(f"  1. 登入 {supabase_url}/project/_/sql")
    print("  2. 執行以下 SQL:\n")
    print("     ALTER TYPE message_role ADD VALUE IF NOT EXISTS 'Humans';")
    print()
    
    print("方法2 - 本地 SQL 檔案:")
    print("  檔案位置: backend/migrations/add_humans_role.sql")
    print("  使用 psql: psql <DATABASE_URL> -f backend/migrations/add_humans_role.sql")
    print()
    
    print("方法3 - Supabase CLI:")
    print("  supabase db execute --file backend/migrations/add_humans_role.sql")
    print()
    
    print("執行後，請重新執行此測試腳本驗證")
    print("="*60)

def main():
    load_env()
    
    print("="*60)
    print("🧪 住宅維修服務 - Humans Role 測試")
    print("="*60)
    
    # 測試連線
    if not test_supabase_connection():
        print("\n⚠️  無法連接 Supabase，請檢查 .env 設定")
        return
    
    # 測試 Humans role
    result = test_humans_role_support()
    
    if result == 'supported':
        print("\n✅ 所有測試通過！")
        print("🎉 可以使用 role='Humans' 儲存客服回覆")
        print("\n建議設定:")
        print("  USE_HUMANS_ROLE=True  ✅ 已設定")
    
    elif result == 'not_supported':
        print("\n⚠️  資料庫需要升級")
        show_migration_guide()
        print("\n暫時建議:")
        print("  USE_HUMANS_ROLE=False  ← 使用舊格式（llm + 前綴）")
    
    elif result == 'fallback':
        print("\n📦 使用舊格式（向下相容）")
        print("  role='llm' + content='[OPERATOR:name]...'")
        print("\n如果想啟用新格式，請:")
        print("  1. 執行 migration（加入 Humans enum 值）")
        print("  2. 設定 USE_HUMANS_ROLE=True")
    
    else:
        print("\n❌ 測試失敗，請檢查錯誤訊息")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
自動執行 Humans role migration
使用 Supabase Management API
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

def apply_migration():
    """執行 migration"""
    print("=" * 60)
    print("🚀 執行 Humans Role Migration")
    print("=" * 60)
    
    load_env()
    
    supabase_url = os.getenv('SUPABASE_URL')
    
    if not supabase_url:
        print("\n❌ 未設定 SUPABASE_URL")
        print("\n請選擇以下方式之一：")
        print("\n方式 1 - 設定 Supabase 環境變數")
        print("  編輯 backend/.env 加入：")
        print("  SUPABASE_URL=https://your-project.supabase.co")
        print("  SUPABASE_KEY=your-anon-key")
        print("  SUPABASE_SERVICE_KEY=your-service-role-key")
        print("\n方式 2 - 手動執行 SQL")
        print("  1. 登入 Supabase Dashboard")
        print(f"  2. 前往 SQL Editor")
        print("  3. 執行以下 SQL：")
        print("\n" + "  " + "-" * 56)
        print("  ALTER TYPE message_role ADD VALUE IF NOT EXISTS 'Humans';")
        print("  " + "-" * 56)
        print("\n執行完成後，重新運行此腳本驗證")
        return False
    
    print(f"\n✅ 找到 Supabase URL: {supabase_url[:40]}...")
    print("\n📋 需要執行的 SQL：")
    print("-" * 60)
    print("ALTER TYPE message_role ADD VALUE IF NOT EXISTS 'Humans';")
    print("-" * 60)
    
    print("\n⚠️  注意：")
    print("  - 此操作不可逆（enum 值無法刪除）")
    print("  - 需要資料庫管理員權限")
    print("  - 不會影響現有資料")
    
    print("\n請在 Supabase Dashboard 執行上述 SQL：")
    print(f"📍 {supabase_url}/project/_/sql")
    
    print("\n執行完成後按 Enter 鍵驗證...")
    input()
    
    # 驗證
    print("\n🔍 驗證 migration...")
    try:
        from supabase_client import get_supabase_client
        
        client = get_supabase_client(prefer_service_role=True)
        
        # 嘗試插入測試訊息
        test_data = {
            'session_id': 'test-humans-' + os.urandom(4).hex(),
            'role': 'Humans',
            'content': '測試 Humans role',
            'source_module': 'test'
        }
        
        result = client.table('chat_messages').insert(test_data).execute()
        
        if result.data:
            msg_id = result.data[0].get('message_id')
            print(f"✅ Migration 成功！")
            print(f"📝 測試訊息 ID: {msg_id}")
            
            # 刪除測試訊息
            client.table('chat_messages').delete().eq('message_id', msg_id).execute()
            print(f"🗑️  測試訊息已清理")
            
            print("\n" + "=" * 60)
            print("🎉 升級完成！")
            print("=" * 60)
            print("\n✅ 現在可以使用 role='Humans' 儲存客服回覆")
            print("✅ USE_HUMANS_ROLE=True 已啟用")
            print("\n📊 可以開始進行資料分析：")
            print("   SELECT COUNT(*) FROM chat_messages WHERE role = 'Humans';")
            return True
        else:
            print("❌ 驗證失敗：無法插入測試資料")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if 'invalid input value for enum message_role' in error_msg:
            print("❌ Migration 尚未執行")
            print("請在 Supabase Dashboard 執行 SQL 後重試")
        else:
            print(f"❌ 驗證失敗: {e}")
        return False

if __name__ == '__main__':
    try:
        success = apply_migration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ 已取消")
        sys.exit(1)

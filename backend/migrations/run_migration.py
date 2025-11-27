#!/usr/bin/env python3
"""
執行資料庫 migration 腳本
用法: python run_migration.py add_humans_role.sql
"""

import sys
import os
from pathlib import Path

# 加入 backend 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
from supabase import create_client, Client

# 載入環境變數
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ 錯誤: 請設定 SUPABASE_URL 和 SUPABASE_KEY 環境變數")
    sys.exit(1)

def run_migration(sql_file: str):
    """執行 SQL migration 檔案"""
    
    # 讀取 SQL 檔案
    sql_path = Path(__file__).parent / sql_file
    if not sql_path.exists():
        print(f"❌ 錯誤: 找不到檔案 {sql_path}")
        sys.exit(1)
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 移除註解和空行
    sql_statements = []
    for line in sql_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('--'):
            sql_statements.append(line)
    
    sql_to_execute = '\n'.join(sql_statements)
    
    if not sql_to_execute.strip():
        print("❌ 錯誤: SQL 檔案為空")
        sys.exit(1)
    
    print(f"📄 讀取 SQL 檔案: {sql_file}")
    print(f"📝 SQL 內容:\n{sql_to_execute}\n")
    
    # 確認執行
    confirm = input("⚠️  確定要執行此 migration? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ 已取消")
        sys.exit(0)
    
    # 執行 SQL
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 使用 rpc 執行 SQL (需要在 Supabase 建立 execute_sql function)
        # 或直接使用 PostgREST API
        
        print("\n⚠️  注意: Supabase Python SDK 不直接支援執行 DDL 語句")
        print("請使用以下方式之一執行 migration:\n")
        
        print("方法1 - Supabase Dashboard:")
        print(f"  1. 登入 {SUPABASE_URL}/project/_/sql")
        print(f"  2. 執行以下 SQL:\n")
        print("  " + sql_to_execute.replace('\n', '\n  '))
        print()
        
        print("方法2 - psql 命令列:")
        print("  psql <DATABASE_URL> -f", sql_path)
        print()
        
        print("方法3 - 使用 Supabase CLI:")
        print(f"  supabase db execute --file {sql_path}")
        print()
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python run_migration.py <sql_file>")
        print("範例: python run_migration.py add_humans_role.sql")
        sys.exit(1)
    
    sql_file = sys.argv[1]
    run_migration(sql_file)

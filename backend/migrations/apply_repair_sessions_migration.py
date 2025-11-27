#!/usr/bin/env python3
"""
repair_sessions 表建立 Migration 執行腳本

使用方式:
    python apply_repair_sessions_migration.py

說明:
    - 讀取 create_repair_sessions.sql 並執行
    - 驗證表格是否建立成功
    - 顯示表結構資訊
"""

import os
import sys
from pathlib import Path

# 加入 backend 路徑以便 import
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / '.env')

from supabase_client import get_supabase_client


def apply_migration():
    """執行 repair_sessions 表建立 Migration"""
    
    print("=" * 60)
    print("repair_sessions 表建立 Migration")
    print("=" * 60)
    print()
    
    # 讀取 SQL 檔案
    sql_file = Path(__file__).parent / 'create_repair_sessions.sql'
    
    if not sql_file.exists():
        print(f"❌ 錯誤: 找不到 SQL 檔案 {sql_file}")
        return False
    
    print(f"📄 讀取 SQL 檔案: {sql_file.name}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print(f"✅ SQL 檔案讀取成功 ({len(sql_content)} 字元)")
    print()
    
    # 取得 Supabase 客戶端
    try:
        client = get_supabase_client(prefer_service_role=True)
        print("✅ Supabase 連線成功")
    except Exception as e:
        print(f"❌ Supabase 連線失敗: {e}")
        return False
    
    print()
    print("🚀 開始執行 Migration...")
    print()
    
    # 執行 SQL (Supabase Python SDK 不直接支援執行 DDL，需要透過 RPC 或手動執行)
    print("⚠️  注意: Supabase Python SDK 不直接支援執行 DDL SQL")
    print()
    print("請使用以下方式之一執行 Migration:")
    print()
    print("方式 1: 透過 Supabase Dashboard")
    print("  1. 登入 https://app.supabase.com")
    print("  2. 選擇專案")
    print("  3. 進入 SQL Editor")
    print("  4. 複製貼上以下 SQL 並執行:")
    print()
    print("-" * 60)
    print(sql_content)
    print("-" * 60)
    print()
    
    print("方式 2: 透過 psql 命令列工具")
    print(f"  psql -h <host> -U postgres -d postgres -f {sql_file}")
    print()
    
    print("方式 3: 透過 Python (使用 psycopg2)")
    print("  執行 apply_repair_sessions_migration_psycopg2.py")
    print()
    
    # 嘗試驗證表是否存在
    print("🔍 驗證表是否已存在...")
    try:
        result = client.table('repair_sessions').select('*').limit(1).execute()
        print("✅ repair_sessions 表已存在!")
        print()
        
        if result.data:
            print("表中已有資料，顯示第一筆:")
            print(f"  欄位: {', '.join(result.data[0].keys())}")
            print()
        else:
            print("表為空 (這是正常的)")
            print()
        
        print("=" * 60)
        print("✅ Migration 驗證完成")
        print("=" * 60)
        return True
        
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg or 'not found' in error_msg:
            print("❌ repair_sessions 表尚未建立")
            print()
            print("請依照上述方式執行 SQL Migration")
        else:
            print(f"⚠️  驗證時發生錯誤: {error_msg}")
        print()
        return False


def verify_migration():
    """驗證 Migration 結果"""
    print()
    print("=" * 60)
    print("驗證 repair_sessions 表結構")
    print("=" * 60)
    print()
    
    try:
        client = get_supabase_client(prefer_service_role=True)
        
        # 測試查詢
        result = client.table('repair_sessions').select('*').limit(1).execute()
        
        print("✅ 表結構驗證成功")
        print()
        
        if result.data:
            print("表欄位:")
            for key in result.data[0].keys():
                print(f"  ✓ {key}")
        else:
            print("⚠️  表為空，無法顯示欄位結構")
            print("   請先手動執行 Migration SQL")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 驗證失敗: {e}")
        print()
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='repair_sessions Migration 工具')
    parser.add_argument(
        '--verify',
        action='store_true',
        help='僅驗證表是否存在，不執行 Migration'
    )
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_migration()
    else:
        success = apply_migration()
    
    sys.exit(0 if success else 1)

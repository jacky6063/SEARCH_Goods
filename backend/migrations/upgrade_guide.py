#!/usr/bin/env python3
"""
快速升級到新格式 - 無需 Supabase 連線
直接顯示需要執行的 SQL 和設定
"""

import os
from pathlib import Path

def main():
    print("=" * 70)
    print("🚀 升級到 Humans Role 新格式")
    print("=" * 70)
    
    print("\n📋 步驟 1：執行資料庫 SQL")
    print("-" * 70)
    print("在您的資料庫管理介面執行以下 SQL：\n")
    print("  ALTER TYPE message_role ADD VALUE IF NOT EXISTS 'Humans';\n")
    print("位置選項：")
    print("  • Supabase Dashboard: https://app.supabase.com → SQL Editor")
    print("  • pgAdmin")
    print("  • psql 命令列")
    print("  • DBeaver 等其他工具")
    
    print("\n" + "=" * 70)
    print("📋 步驟 2：確認環境設定")
    print("-" * 70)
    
    env_file = Path(__file__).parent.parent / '.env'
    
    if env_file.exists():
        with open(env_file) as f:
            content = f.read()
            
        if 'USE_HUMANS_ROLE=True' in content:
            print("✅ USE_HUMANS_ROLE=True 已設定")
        else:
            print("⚠️  建議在 .env 檔案加入：")
            print("   USE_HUMANS_ROLE=True")
    else:
        print("⚠️  找不到 .env 檔案")
    
    print("\n" + "=" * 70)
    print("📋 步驟 3：重新啟動後端服務")
    print("-" * 70)
    print("cd backend")
    print(".venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    
    print("\n" + "=" * 70)
    print("✅ 升級完成後的效果")
    print("-" * 70)
    print("\n資料庫寫入：")
    print("  role: 'Humans'")
    print("  content: '您好...'（無前綴）")
    print("\n資料分析：")
    print("  SELECT COUNT(*) FROM chat_messages WHERE role = 'Humans';")
    print("  SELECT session_id FROM chat_messages WHERE role = 'Humans';")
    
    print("\n" + "=" * 70)
    print("📊 新舊格式對照")
    print("-" * 70)
    print("舊格式（向下相容）:")
    print("  role: 'llm'")
    print("  content: '[OPERATOR:小美]您好...'")
    print("\n新格式（推薦）:")
    print("  role: 'Humans'")
    print("  content: '您好...'")
    print("\n✅ 前端自動支援兩種格式")
    print("=" * 70)
    
    print("\n⚠️  重要提醒：")
    print("  • SQL 執行後無法還原（enum 值不可刪除）")
    print("  • 建議先在測試環境執行")
    print("  • 執行前請備份資料庫")
    
    print("\n" + "=" * 70)
    print("📁 相關檔案：")
    print("  • SQL 腳本: backend/migrations/add_humans_role.sql")
    print("  • 升級指南: backend/migrations/UPGRADE_GUIDE.md")
    print("  • 環境設定: backend/.env")
    print("=" * 70)

if __name__ == '__main__':
    main()

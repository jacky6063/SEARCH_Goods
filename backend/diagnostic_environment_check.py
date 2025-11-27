#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
環境一致性診斷工具
================================================================================

目的：診斷本地端與生產端的環境差異，找出影響查詢結果的所有因素

使用方式：
    python diagnostic_environment_check.py

輸出：
    - 環境變數差異
    - 資料檔案差異
    - 快取狀態
    - 程式碼版本差異
    - 配置檔差異
================================================================================
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import hashlib

# 加入 backend 路徑
sys.path.insert(0, str(Path(__file__).parent))

def get_file_hash(filepath: str) -> str:
    """計算檔案 MD5 hash"""
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    except Exception as e:
        return f"ERROR: {e}"

def check_environment_vars() -> Dict[str, Any]:
    """檢查關鍵環境變數"""
    key_vars = [
        'DATA_PATH',
        'CATEGORIES_PATH',
        'DEFAULT_PAGE_SIZE',
        'HOT_CATEGORY_PAGE_SIZE',
        'OPENAI_API_KEY',
        'USE_LLM_EXPAND',
        'USE_LLM_RERANK',
        'USE_LLM_SHORTDESC',
        'SEARCH_USE_EXPAND',
        'SEARCH_USE_RERANK',
        'PYTHONPATH',
        'PORT',
    ]
    
    env_status = {}
    for var in key_vars:
        value = os.getenv(var)
        if value:
            # 隱藏敏感資訊
            if 'KEY' in var or 'TOKEN' in var or 'SECRET' in var:
                env_status[var] = f"SET (***{value[-4:]})" if len(value) > 4 else "SET"
            else:
                env_status[var] = value
        else:
            env_status[var] = "NOT_SET"
    
    return env_status

def check_data_files() -> Dict[str, Any]:
    """檢查資料檔案狀態"""
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    
    files_status = {}
    
    # 檢查主要資料檔
    csv_file = data_dir / "VIEW_GOODS_enhanced.csv"
    if csv_file.exists():
        stat = csv_file.stat()
        df = pd.read_csv(csv_file)
        files_status['VIEW_GOODS_enhanced.csv'] = {
            'exists': True,
            'size_mb': round(stat.st_size / 1024 / 1024, 2),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'rows': len(df),
            'columns': len(df.columns),
            'hash': get_file_hash(str(csv_file)),
            'l3_categories': df['小分類名稱'].nunique() if '小分類名稱' in df.columns else 'N/A',
        }
        
        # 檢查關鍵欄位
        required_cols = ['商品編號', '商品名稱', '大分類名稱', '中分類名稱', '小分類名稱']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            files_status['VIEW_GOODS_enhanced.csv']['missing_columns'] = missing_cols
        
        # 檢查是否有 CateName 欄位（新版）
        catename_cols = [col for col in df.columns if 'CateName' in col]
        files_status['VIEW_GOODS_enhanced.csv']['has_catename_columns'] = len(catename_cols) > 0
        files_status['VIEW_GOODS_enhanced.csv']['catename_columns'] = catename_cols
    else:
        files_status['VIEW_GOODS_enhanced.csv'] = {'exists': False}
    
    # 檢查分類檔案
    cat_file = data_dir / "goods_categories.csv"
    if cat_file.exists():
        stat = cat_file.stat()
        df_cat = pd.read_csv(cat_file)
        files_status['goods_categories.csv'] = {
            'exists': True,
            'size_kb': round(stat.st_size / 1024, 2),
            'rows': len(df_cat),
            'hash': get_file_hash(str(cat_file)),
        }
    else:
        files_status['goods_categories.csv'] = {'exists': False}
    
    return files_status

def check_code_versions() -> Dict[str, Any]:
    """檢查關鍵程式碼檔案的版本（透過 hash）"""
    root = Path(__file__).resolve().parents[1]
    backend_dir = root / "backend"
    frontend_dir = root / "frontend"
    
    code_files = {
        'backend/app.py': backend_dir / "app.py",
        'backend/goods_search_service.py': backend_dir / "goods_search_service.py",
        'backend/services/categories_service.py': backend_dir / "services" / "categories_service.py",
        'frontend/index.html': frontend_dir / "index.html",
    }
    
    versions = {}
    for name, filepath in code_files.items():
        if filepath.exists():
            versions[name] = {
                'hash': get_file_hash(str(filepath)),
                'size_kb': round(filepath.stat().st_size / 1024, 2),
                'modified': datetime.fromtimestamp(filepath.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            }
        else:
            versions[name] = {'exists': False}
    
    return versions

def check_config_files() -> Dict[str, Any]:
    """檢查配置檔案"""
    root = Path(__file__).resolve().parents[1]
    backend_dir = root / "backend"
    
    config_files = {
        'column_definitions.json': backend_dir / "column_definitions.json",
        'branding_config.json': backend_dir / "branding_config.json",
        '.env.dev': backend_dir / ".env.dev",
        '.env.test': backend_dir / ".env.test",
    }
    
    configs = {}
    for name, filepath in config_files.items():
        if filepath.exists():
            configs[name] = {
                'exists': True,
                'hash': get_file_hash(str(filepath)),
                'size_bytes': filepath.stat().st_size,
            }
            
            # 讀取內容（排除敏感資訊）
            if filepath.suffix == '.json':
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if name == 'branding_config.json':
                            configs[name]['content'] = {
                                'has_logo': bool(data.get('logo_url')),
                                'has_youtube': bool(data.get('youtube_url')),
                                'voice_mode_enabled': data.get('voice_mode_enabled', False),
                            }
                except Exception as e:
                    configs[name]['error'] = str(e)
        else:
            configs[name] = {'exists': False}
    
    return configs

def check_runtime_imports() -> Dict[str, Any]:
    """檢查關鍵模組的載入狀態"""
    imports_status = {}
    
    try:
        import goods_search_service
        imports_status['goods_search_service'] = {
            'loaded': True,
            'path': str(Path(goods_search_service.__file__).resolve()),
        }
    except Exception as e:
        imports_status['goods_search_service'] = {'loaded': False, 'error': str(e)}
    
    try:
        from services import categories_service
        imports_status['categories_service'] = {
            'loaded': True,
            'path': str(Path(categories_service.__file__).resolve()),
        }
    except Exception as e:
        imports_status['categories_service'] = {'loaded': False, 'error': str(e)}
    
    return imports_status

def simulate_hot_category_query() -> Dict[str, Any]:
    """模擬熱門分類查詢，檢查實際結果"""
    try:
        # 載入資料
        root = Path(__file__).resolve().parents[1]
        csv_file = root / "data" / "VIEW_GOODS_enhanced.csv"
        
        if not csv_file.exists():
            return {'error': 'CSV file not found'}
        
        df = pd.read_csv(csv_file)
        
        # 模擬查詢「籃球鞋」（L3 分類）
        l3_name = "籃球鞋"
        
        # 方法 1：直接過濾 L3
        if '小分類名稱' in df.columns:
            result_direct = df[df['小分類名稱'] == l3_name]
        else:
            result_direct = pd.DataFrame()
        
        # 方法 2：透過 CateName_L3 過濾
        if 'CateName_L3' in df.columns:
            result_catename = df[df['CateName_L3'] == l3_name]
        else:
            result_catename = pd.DataFrame()
        
        return {
            'test_category': l3_name,
            'method_1_小分類名稱': {
                'column_exists': '小分類名稱' in df.columns,
                'result_count': len(result_direct),
            },
            'method_2_CateName_L3': {
                'column_exists': 'CateName_L3' in df.columns,
                'result_count': len(result_catename),
            },
            'note': '生產環境應該回傳 6 筆（可能是 page_size 限制）',
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    """執行完整診斷"""
    print("=" * 80)
    print("🔍 SEARCH_Goods 環境一致性診斷工具")
    print("=" * 80)
    print()
    
    # 1. 環境變數
    print("📋 1. 環境變數檢查")
    print("-" * 80)
    env_vars = check_environment_vars()
    for key, value in env_vars.items():
        status = "✅" if value != "NOT_SET" else "❌"
        print(f"{status} {key:30s} = {value}")
    print()
    
    # 2. 資料檔案
    print("📂 2. 資料檔案檢查")
    print("-" * 80)
    files = check_data_files()
    for filename, info in files.items():
        if info.get('exists'):
            print(f"✅ {filename}")
            for key, value in info.items():
                if key != 'exists':
                    print(f"   - {key}: {value}")
        else:
            print(f"❌ {filename} - 不存在")
    print()
    
    # 3. 程式碼版本
    print("💾 3. 程式碼版本檢查 (Hash)")
    print("-" * 80)
    versions = check_code_versions()
    for filename, info in versions.items():
        if info.get('exists') is False:
            print(f"❌ {filename} - 不存在")
        else:
            print(f"✅ {filename}")
            print(f"   Hash: {info['hash']}")
            print(f"   修改時間: {info['modified']}")
    print()
    
    # 4. 配置檔案
    print("⚙️  4. 配置檔案檢查")
    print("-" * 80)
    configs = check_config_files()
    for filename, info in configs.items():
        if info.get('exists'):
            print(f"✅ {filename}")
            print(f"   Hash: {info['hash']}")
            if 'content' in info:
                for key, value in info['content'].items():
                    print(f"   - {key}: {value}")
        else:
            print(f"❌ {filename} - 不存在")
    print()
    
    # 5. 模組載入
    print("📦 5. 模組載入檢查")
    print("-" * 80)
    imports = check_runtime_imports()
    for module, info in imports.items():
        if info['loaded']:
            print(f"✅ {module}")
            print(f"   Path: {info['path']}")
        else:
            print(f"❌ {module} - {info['error']}")
    print()
    
    # 6. 模擬查詢
    print("🧪 6. 模擬熱門分類查詢")
    print("-" * 80)
    query_result = simulate_hot_category_query()
    if 'error' in query_result:
        print(f"❌ 查詢失敗: {query_result['error']}")
    else:
        print(f"測試分類: {query_result['test_category']}")
        print(f"\n方法 1 (小分類名稱):")
        print(f"  - 欄位存在: {query_result['method_1_小分類名稱']['column_exists']}")
        print(f"  - 查詢結果: {query_result['method_1_小分類名稱']['result_count']} 筆")
        print(f"\n方法 2 (CateName_L3):")
        print(f"  - 欄位存在: {query_result['method_2_CateName_L3']['column_exists']}")
        print(f"  - 查詢結果: {query_result['method_2_CateName_L3']['result_count']} 筆")
        print(f"\n⚠️  {query_result['note']}")
    print()
    
    # 7. 總結與建議
    print("=" * 80)
    print("📝 診斷總結與建議")
    print("=" * 80)
    
    issues = []
    
    # 檢查 DATA_PATH
    if env_vars.get('DATA_PATH') == 'NOT_SET':
        issues.append("❌ DATA_PATH 未設定（可能使用預設路徑）")
    
    # 檢查資料檔案
    csv_info = files.get('VIEW_GOODS_enhanced.csv', {})
    if not csv_info.get('exists'):
        issues.append("❌ 主資料檔案不存在")
    elif csv_info.get('rows', 0) < 100:
        issues.append(f"⚠️  資料行數偏少 ({csv_info.get('rows')} 筆)")
    
    # 檢查欄位結構
    if csv_info.get('has_catename_columns') is False:
        issues.append("⚠️  缺少 CateName 系列欄位（可能需要欄位對應）")
    
    # 檢查查詢結果
    if query_result.get('method_1_小分類名稱', {}).get('result_count') == 0:
        issues.append("❌ 測試查詢沒有結果（資料可能有問題）")
    
    if issues:
        print("\n⚠️  發現的問題：")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ 所有檢查項目正常")
    
    print("\n💡 下一步建議：")
    print("  1. 將此診斷報告與生產環境比對")
    print("  2. 特別注意 hash 值差異（代表程式碼或資料不同）")
    print("  3. 檢查生產環境的 page_size 設定")
    print("  4. 確認生產環境的資料檔案日期和筆數")
    print()

if __name__ == "__main__":
    main()

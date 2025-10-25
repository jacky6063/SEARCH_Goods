#!/usr/bin/env python3
"""
欄位標準化驗證腳本
檢查系統中所有檔案是否使用統一的欄位存取方式
"""

import os
import re
import sys
from pathlib import Path

def scan_field_usage(directory: str) -> dict:
    """掃描目錄中的 Python 檔案，查找欄位使用情況"""
    field_usage = {}
    python_files = Path(directory).rglob("*.py")
    
    # 需要檢查的欄位模式
    field_patterns = [
        r'\.get\(["\']([^"\']+)["\']\)',  # .get("field_name")
        r'\[["\'](GoodIden|Name|CateName|BRAND_Name|DESCRIPTION|商品名稱|商品編號|分類名稱|品牌|描述)["\']\]',  # ["field_name"]
    ]
    
    for file_path in python_files:
        if "field_utils.py" in str(file_path) or "__pycache__" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in field_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    field_name = match if isinstance(match, str) else match[0]
                    if field_name in ['GoodIden', 'Name', 'CateName', 'BRAND_Name', 'DESCRIPTION', 
                                    'Price', 'SpecialOffer', 'Size', '商品名稱', '商品編號', '分類名稱', 
                                    '品牌', '描述', '售價', '特價', '規格']:
                        
                        if field_name not in field_usage:
                            field_usage[field_name] = []
                        field_usage[field_name].append(str(file_path.relative_to(Path(directory))))
                        
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
    
    return field_usage

def check_field_accessor_usage(directory: str) -> list:
    """檢查哪些檔案使用了 FieldAccessor"""
    using_field_accessor = []
    python_files = Path(directory).rglob("*.py")
    
    for file_path in python_files:
        if "field_utils.py" in str(file_path) or "__pycache__" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if "FieldAccessor" in content or "field_utils" in content:
                using_field_accessor.append(str(file_path.relative_to(Path(directory))))
                
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
    
    return using_field_accessor

def generate_migration_suggestions(field_usage: dict) -> list:
    """產生遷移建議"""
    suggestions = []
    
    # 檢查直接存取欄位的檔案
    direct_access_files = set()
    for field_name, files in field_usage.items():
        if field_name in ['GoodIden', 'Name', 'CateName', 'BRAND_Name', 'DESCRIPTION', 
                         'Price', 'SpecialOffer', 'Size', '商品名稱', '商品編號', '分類名稱', 
                         '品牌', '描述', '售價', '特價', '規格']:
            direct_access_files.update(files)
    
    for file_path in direct_access_files:
        suggestions.append({
            "file": file_path,
            "suggestion": "建議使用 FieldAccessor 統一存取欄位",
            "example": "將 item.get('Name') 改為 FieldAccessor.get_name(item)"
        })
    
    return suggestions

def main():
    backend_dir = "."
    
    print("🔍 欄位標準化驗證報告")
    print("=" * 50)
    
    # 1. 掃描欄位使用情況
    print("\n📋 欄位使用情況掃描:")
    field_usage = scan_field_usage(backend_dir)
    
    for field_name, files in sorted(field_usage.items()):
        print(f"  {field_name}: {len(files)} 個檔案")
        for file_path in files[:3]:  # 只顯示前3個
            print(f"    - {file_path}")
        if len(files) > 3:
            print(f"    ... 還有 {len(files) - 3} 個檔案")
    
    # 2. 檢查 FieldAccessor 使用情況
    print(f"\n✅ 使用 FieldAccessor 的檔案:")
    using_field_accessor = check_field_accessor_usage(backend_dir)
    
    if using_field_accessor:
        for file_path in using_field_accessor:
            print(f"  ✓ {file_path}")
    else:
        print("  ❌ 沒有檔案使用 FieldAccessor")
    
    # 3. 產生遷移建議
    print(f"\n💡 遷移建議:")
    suggestions = generate_migration_suggestions(field_usage)
    
    if suggestions:
        for suggestion in suggestions[:5]:  # 只顯示前5個建議
            print(f"  📁 {suggestion['file']}")
            print(f"     建議: {suggestion['suggestion']}")
            print(f"     範例: {suggestion['example']}")
    else:
        print("  🎉 所有檔案都已使用標準化欄位存取方式")
    
    # 4. 統計摘要
    total_files_with_field_access = len(set(sum(field_usage.values(), [])))
    files_using_field_accessor = len(using_field_accessor)
    migration_progress = (files_using_field_accessor / total_files_with_field_access * 100) if total_files_with_field_access > 0 else 0
    
    print(f"\n📊 標準化進度:")
    print(f"  總共有欄位存取的檔案: {total_files_with_field_access}")
    print(f"  已使用 FieldAccessor: {files_using_field_accessor}")
    print(f"  標準化進度: {migration_progress:.1f}%")
    
    if migration_progress >= 80:
        print(f"  🎉 標準化進度良好!")
    elif migration_progress >= 50:
        print(f"  📈 標準化進度中等，建議繼續改進")
    else:
        print(f"  ⚠️  標準化進度較低，建議優先處理")

if __name__ == "__main__":
    main()
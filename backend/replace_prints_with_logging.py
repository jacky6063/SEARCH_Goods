#!/usr/bin/env python3
"""
批量替換 print 語句為 logging 語句
"""
import re
import sys
from pathlib import Path

def replace_prints_in_file(filepath: Path) -> tuple[int, bool]:
    """
    替換檔案中的 print 語句為 logging 語句
    
    Returns:
        (替換次數, 是否有修改)
    """
    try:
        content = filepath.read_text(encoding='utf-8')
        original_content = content
        count = 0
        
        # 替換規則
        replacements = [
            # DEBUG 級別
            (r'print\(f?"\[DEBUG\] ([^"]+)"\)', r'_logger.debug("\1")'),
            (r"print\(f?'\[DEBUG\] ([^']+)'\)", r"_logger.debug('\1')"),
            
            # INFO 級別
            (r'print\(f?"\[INFO\] ([^"]+)"\)', r'_logger.info("\1")'),
            (r"print\(f?'\[INFO\] ([^']+)'\)", r"_logger.info('\1')"),
            
            # WARNING 級別
            (r'print\(f?"\[WARNING\] ([^"]+)"\)', r'_logger.warning("\1")'),
            (r"print\(f?'\[WARNING\] ([^']+)'\)", r"_logger.warning('\1')"),
            (r'print\(f?"\[WARN\] ([^"]+)"\)', r'_logger.warning("\1")'),
            (r"print\(f?'\[WARN\] ([^']+)'\)", r"_logger.warning('\1')"),
            
            # ERROR 級別
            (r'print\(f?"\[ERROR\] ([^"]+)"\)', r'_logger.error("\1")'),
            (r"print\(f?'\[ERROR\] ([^']+)'\)", r"_logger.error('\1')"),
        ]
        
        for pattern, replacement in replacements:
            new_content, n = re.subn(pattern, replacement, content)
            if n > 0:
                content = new_content
                count += n
        
        # 如果有修改，寫回檔案
        if content != original_content:
            filepath.write_text(content, encoding='utf-8')
            return count, True
        
        return 0, False
    
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return 0, False


def main():
    """主程式"""
    backend_dir = Path(__file__).parent
    
    files_to_process = [
        backend_dir / "llm_service.py",
        backend_dir / "chat_router_goods_action.py",
    ]
    
    total_replacements = 0
    files_modified = 0
    
    for filepath in files_to_process:
        if not filepath.exists():
            print(f"File not found: {filepath}")
            continue
        
        print(f"Processing {filepath.name}...", end=" ")
        count, modified = replace_prints_in_file(filepath)
        
        if modified:
            print(f"✓ {count} replacements")
            total_replacements += count
            files_modified += 1
        else:
            print("⊘ no changes")
    
    print(f"\nSummary:")
    print(f"  Files modified: {files_modified}")
    print(f"  Total replacements: {total_replacements}")


if __name__ == "__main__":
    main()

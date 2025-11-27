#!/usr/bin/env python3
"""
分析文檔並識別過時的文件
"""
import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Set

def categorize_docs(root_path: Path) -> Dict[str, List[Path]]:
    """根據文件名和內容分類文檔"""
    categories = {
        "部署相關": [],
        "聊天功能": [],
        "搜尋功能": [],
        "分類系統": [],
        "LLM功能": [],
        "欄位標準化": [],
        "測試報告": [],
        "修復記錄": [],
        "開發指南": [],
        "架構設計": [],
        "維修服務": [],
        "Supabase整合": [],
        "CI/CD": [],
        "審查報告": [],
        "其他": []
    }
    
    # 關鍵字映射
    keyword_mapping = {
        "部署相關": ["deployment", "部署", "deploy", "render", "netlify", "生產", "production"],
        "聊天功能": ["chat", "聊天", "對話", "conversation", "意圖", "intent"],
        "搜尋功能": ["search", "搜尋", "query", "商品查詢", "goods_search"],
        "分類系統": ["category", "分類", "L1", "L2", "L3", "hierarchy", "階層"],
        "LLM功能": ["llm", "openai", "gpt", "ai", "語言模型"],
        "欄位標準化": ["field", "欄位", "column", "標準化", "standardization"],
        "測試報告": ["test", "測試", "驗證", "validation"],
        "修復記錄": ["fix", "修復", "bug", "問題", "診斷", "diagnosis"],
        "開發指南": ["guide", "指南", "setup", "環境", "開發"],
        "架構設計": ["architecture", "架構", "design", "設計", "規劃"],
        "維修服務": ["repair", "維修", "住宅"],
        "Supabase整合": ["supabase", "database", "資料庫"],
        "CI/CD": ["ci", "cd", "github", "workflow", "action"],
        "審查報告": ["review", "審查", "code_review", "評估", "evaluation"]
    }
    
    for md_file in root_path.rglob("*.md"):
        file_name = md_file.name.lower()
        categorized = False
        
        for category, keywords in keyword_mapping.items():
            if any(kw in file_name for kw in keywords):
                categories[category].append(md_file)
                categorized = True
                break
        
        if not categorized:
            categories["其他"].append(md_file)
    
    return categories

def extract_date_from_filename(filename: str) -> datetime | None:
    """從檔名中提取日期"""
    # 匹配 20241030, 2024-10-30, 20251025_223605 等格式
    patterns = [
        r'(\d{8})',  # 20241030
        r'(\d{4}-\d{2}-\d{2})',  # 2024-10-30
        r'(\d{8})_\d{6}',  # 20251025_223605
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            date_str = match.group(1).replace('-', '')
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except:
                pass
    return None

def check_if_outdated(file_path: Path, current_code_files: Set[str]) -> Dict[str, any]:
    """檢查文檔是否過時"""
    result = {
        "path": file_path,
        "is_outdated": False,
        "reasons": [],
        "confidence": 0.0
    }
    
    filename = file_path.name
    
    # 1. 檢查日期（超過6個月的可能過時）
    file_date = extract_date_from_filename(filename)
    if file_date:
        days_old = (datetime.now() - file_date).days
        if days_old > 180:  # 6個月
            result["is_outdated"] = True
            result["reasons"].append(f"文件日期超過6個月 ({days_old}天)")
            result["confidence"] += 0.3
    
    # 2. 檢查是否為測試報告/修復記錄（通常是一次性的）
    if any(kw in filename.lower() for kw in ["test_report", "測試報告", "fix", "修復記錄", "診斷"]):
        result["is_outdated"] = True
        result["reasons"].append("測試報告或修復記錄（一次性文檔）")
        result["confidence"] += 0.4
    
    # 3. 檢查是否包含特定版本號或階段標記
    if any(kw in filename.lower() for kw in ["phase_1", "phase_2", "v1", "v2", "_bak", ".bak"]):
        result["is_outdated"] = True
        result["reasons"].append("包含版本號或階段標記")
        result["confidence"] += 0.5
    
    # 4. 檢查是否為完成報告（Complete, 完成）
    if any(kw in filename.lower() for kw in ["complete", "完成", "總結", "summary"]):
        result["is_outdated"] = True
        result["reasons"].append("完成報告（歷史記錄）")
        result["confidence"] += 0.3
    
    # 5. 讀取內容檢查（簡化版，只讀前500行）
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')[:500]
        content_sample = '\n'.join(lines)
        
        # 檢查是否提到已不存在的檔案
        mentioned_files = re.findall(r'`([a-zA-Z0-9_/]+\.py)`', content_sample)
        missing_files = [f for f in mentioned_files if f not in current_code_files]
        
        if len(missing_files) > 3:  # 超過3個不存在的檔案
            result["is_outdated"] = True
            result["reasons"].append(f"提到多個不存在的檔案 ({len(missing_files)}個)")
            result["confidence"] += 0.2
        
        # 檢查是否包含「已棄用」、「過時」等字樣
        if any(kw in content_sample for kw in ["已棄用", "過時", "deprecated", "obsolete"]):
            result["is_outdated"] = True
            result["reasons"].append("內容標註為過時")
            result["confidence"] += 0.8
    
    except Exception as e:
        pass
    
    return result

def get_current_code_files(root_path: Path) -> Set[str]:
    """獲取當前所有程式碼檔案"""
    code_files = set()
    for ext in ['.py', '.js', '.ts', '.jsx', '.tsx']:
        for file in root_path.rglob(f"*{ext}"):
            code_files.add(file.name)
    return code_files

def analyze_docs():
    """主分析函數"""
    root = Path("/Users/huangchangchi/Documents/SEARCH_Goods")
    
    print("🔍 開始分析文檔...")
    print("=" * 80)
    
    # 獲取當前程式碼檔案
    current_code_files = get_current_code_files(root)
    print(f"✓ 找到 {len(current_code_files)} 個程式碼檔案")
    
    # 分類文檔
    categories = categorize_docs(root)
    total_docs = sum(len(docs) for docs in categories.values())
    print(f"✓ 找到 {total_docs} 個 Markdown 文檔")
    print()
    
    # 顯示分類統計
    print("📊 文檔分類統計:")
    print("-" * 80)
    for category, docs in categories.items():
        if docs:
            print(f"  {category:20s}: {len(docs):3d} 個")
    print()
    
    # 檢查過時文檔
    print("🔍 檢查過時文檔...")
    print("-" * 80)
    
    outdated_docs = []
    for category, docs in categories.items():
        for doc in docs:
            result = check_if_outdated(doc, current_code_files)
            if result["is_outdated"] and result["confidence"] > 0.5:
                outdated_docs.append((category, result))
    
    # 輸出結果
    print(f"\n⚠️  找到 {len(outdated_docs)} 個可能過時的文檔:")
    print("=" * 80)
    
    by_category = defaultdict(list)
    for category, result in outdated_docs:
        by_category[category].append(result)
    
    for category, results in sorted(by_category.items()):
        print(f"\n【{category}】 ({len(results)} 個)")
        print("-" * 80)
        for r in sorted(results, key=lambda x: x["confidence"], reverse=True):
            rel_path = r["path"].relative_to(root)
            print(f"  📄 {rel_path}")
            print(f"     信心度: {r['confidence']:.1f}")
            print(f"     原因: {', '.join(r['reasons'])}")
            print()
    
    # 生成報告檔案
    report_path = root / "DOC_ANALYSIS_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 文檔分析報告\n\n")
        f.write(f"**分析日期**: {datetime.now().strftime('%Y年%m月%d日')}\n\n")
        f.write(f"**總文檔數**: {total_docs}\n")
        f.write(f"**可能過時**: {len(outdated_docs)}\n\n")
        
        f.write("## 文檔分類統計\n\n")
        for category, docs in categories.items():
            if docs:
                f.write(f"- **{category}**: {len(docs)} 個\n")
        
        f.write("\n## 可能過時的文檔\n\n")
        for category, results in sorted(by_category.items()):
            f.write(f"### {category} ({len(results)} 個)\n\n")
            for r in sorted(results, key=lambda x: x["confidence"], reverse=True):
                rel_path = r["path"].relative_to(root)
                f.write(f"#### `{rel_path}`\n\n")
                f.write(f"- **信心度**: {r['confidence']:.1f}\n")
                f.write(f"- **原因**:\n")
                for reason in r['reasons']:
                    f.write(f"  - {reason}\n")
                f.write("\n")
    
    print(f"\n✅ 分析報告已生成: {report_path}")

if __name__ == "__main__":
    analyze_docs()

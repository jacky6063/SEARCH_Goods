#!/usr/bin/env python3
"""
分析 CSV 商品數據,自動生成分類範例
用於優化 LLM Prompt 中的【重要分類範例】
"""

import pandas as pd
from collections import defaultdict
import os

# CSV 路徑
CSV_PATH = os.path.join(os.path.dirname(__file__), "../data/VIEW_GOODS_enhanced.csv")

def load_data():
    """載入商品數據"""
    df = pd.read_csv(CSV_PATH)
    print(f"✅ 載入 {len(df)} 筆商品資料\n")
    return df

def simplify_product_name(name):
    """
    簡化商品名稱,移除規格、重量、品牌等資訊
    範例: "有機白米/2kg" -> "有機白米"
    """
    if pd.isna(name):
        return ""
    
    name = str(name)
    
    # 移除 "/" 後的內容 (規格)
    if "/" in name:
        name = name.split("/")[0]
    
    # 移除 "(" 後的內容 (註解)
    if "(" in name:
        name = name.split("(")[0]
    
    # 移除常見的重量單位
    for unit in ["g", "ml", "kg", "公克", "毫升", "公斤", "*", "x"]:
        if unit in name:
            # 找到數字+單位的位置並移除
            import re
            name = re.sub(r'\d+' + unit + r'.*', '', name)
    
    return name.strip()

def extract_category_examples(df, top_n=5):
    """
    從 CSV 自動提取每個分類的商品範例
    
    參數:
        df: 商品數據 DataFrame
        top_n: 每個分類取前 N 個商品
    
    返回:
        dict: {分類路徑: [商品名稱列表]}
    """
    examples = defaultdict(list)
    
    # 按 L1 > L2 > L3 分組
    grouped = df.groupby(["大分類名稱", "中分類名稱", "小分類名稱"])
    
    for (l1, l2, l3), group in grouped:
        if pd.isna(l1) or pd.isna(l2) or pd.isna(l3):
            continue
        
        # 取前 top_n 個商品名稱
        product_names = group["商品名稱"].head(top_n).tolist()
        
        # 簡化商品名稱
        simplified_names = [simplify_product_name(name) for name in product_names]
        simplified_names = [name for name in simplified_names if name]  # 移除空字串
        
        # 建立分類路徑
        path = f"{l1} > {l2} > {l3}"
        examples[path] = simplified_names[:3]  # 只保留前 3 個
    
    return dict(examples)

def format_examples_for_prompt(examples):
    """
    將範例格式化為適合 LLM Prompt 的文字
    
    按 L1 分組,階層式顯示
    """
    # 按 L1 分組
    l1_groups = defaultdict(lambda: defaultdict(list))
    
    for path, products in examples.items():
        parts = path.split(" > ")
        if len(parts) == 3:
            l1, l2, l3 = parts
            l1_groups[l1][l2].append((l3, products))
    
    # 格式化輸出
    output_lines = []
    output_lines.append("【🆕 自動生成的重要分類範例】\n")
    
    for l1 in sorted(l1_groups.keys()):
        output_lines.append(f"📁 {l1}:")
        
        for l2 in sorted(l1_groups[l1].keys()):
            output_lines.append(f"  ├─ {l2}:")
            
            for l3, products in l1_groups[l1][l2]:
                products_str = "、".join(products[:3])
                output_lines.append(f"  │   └─ {l3}: {products_str}")
        
        output_lines.append("")  # 空行分隔
    
    return "\n".join(output_lines)

def generate_python_dict(examples):
    """
    生成 Python 字典格式的範例代碼
    可直接複製到 llm_service.py 中使用
    """
    output_lines = []
    output_lines.append("# 自動生成的分類範例字典 (可直接使用)")
    output_lines.append("CATEGORY_EXAMPLES_AUTO = {")
    
    # 按 L1 分組
    l1_groups = defaultdict(lambda: defaultdict(list))
    
    for path, products in examples.items():
        parts = path.split(" > ")
        if len(parts) == 3:
            l1, l2, l3 = parts
            l1_groups[l1][l2].append((l3, products))
    
    for l1 in sorted(l1_groups.keys()):
        output_lines.append(f'    "{l1}": {{')
        
        for l2 in sorted(l1_groups[l1].keys()):
            output_lines.append(f'        "{l2}": {{')
            
            for l3, products in l1_groups[l1][l2]:
                products_repr = repr(products)
                output_lines.append(f'            "{l3}": {products_repr},')
            
            output_lines.append('        },')
        
        output_lines.append('    },')
    
    output_lines.append("}")
    
    return "\n".join(output_lines)

def analyze_important_categories(df):
    """
    分析哪些分類最重要 (商品數量最多)
    這些分類應該優先顯示在 Prompt 中
    """
    print("\n" + "="*80)
    print("📊 分類商品數量統計 (Top 20)")
    print("="*80 + "\n")
    
    # 統計每個 L3 分類的商品數量
    l3_counts = df.groupby(["大分類名稱", "中分類名稱", "小分類名稱"]).size()
    l3_counts = l3_counts.sort_values(ascending=False).head(20)
    
    for (l1, l2, l3), count in l3_counts.items():
        print(f"{count:3d} 件 | {l1} > {l2} > {l3}")
    
    return l3_counts

def identify_problematic_categories(examples):
    """
    識別可能需要手動補充的問題分類
    
    問題分類特徵:
    1. 分類名稱與商品名稱差異大
    2. 分類名稱較抽象 (如「烹調食材」)
    3. 商品名稱過於簡短或不明確
    """
    print("\n" + "="*80)
    print("⚠️  建議手動補充的問題分類 (LLM 可能誤判)")
    print("="*80 + "\n")
    
    problematic = []
    
    # 檢查「烹調食材」這類抽象分類
    abstract_keywords = ["烹調食材", "其他", "雜項", "配件", "用品"]
    
    for path, products in examples.items():
        l3 = path.split(" > ")[-1] if " > " in path else path
        
        # 檢查 L3 是否包含抽象關鍵字
        if any(keyword in l3 for keyword in abstract_keywords):
            problematic.append((path, products, "抽象分類名稱"))
        
        # 檢查商品名稱是否過短
        elif all(len(p) <= 4 for p in products):
            problematic.append((path, products, "商品名稱過短"))
    
    for path, products, reason in problematic[:10]:  # 只顯示前 10 個
        products_str = "、".join(products)
        print(f"❌ {path}")
        print(f"   商品: {products_str}")
        print(f"   原因: {reason}\n")
    
    return problematic

def main():
    """主函數"""
    print("="*80)
    print("🔍 開始分析商品分類範例")
    print("="*80 + "\n")
    
    # 1. 載入數據
    df = load_data()
    
    # 2. 提取分類範例
    print("⚙️  提取分類範例...")
    examples = extract_category_examples(df, top_n=5)
    print(f"✅ 成功提取 {len(examples)} 個分類的商品範例\n")
    
    # 3. 格式化為 Prompt 文字
    prompt_text = format_examples_for_prompt(examples)
    print("="*80)
    print("📝 格式化後的 LLM Prompt 範例:")
    print("="*80)
    print(prompt_text)
    
    # 4. 生成 Python 字典代碼
    print("\n" + "="*80)
    print("💻 Python 字典格式 (前 30 行預覽):")
    print("="*80 + "\n")
    python_code = generate_python_dict(examples)
    print("\n".join(python_code.split("\n")[:30]))
    print("... (省略後續內容) ...\n")
    
    # 5. 分析重要分類
    analyze_important_categories(df)
    
    # 6. 識別問題分類
    identify_problematic_categories(examples)
    
    # 7. 輸出完整代碼到文件
    output_file = os.path.join(os.path.dirname(__file__), "category_examples_generated.py")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(python_code)
    
    print("\n" + "="*80)
    print(f"✅ 完整代碼已輸出到: {output_file}")
    print("="*80 + "\n")
    
    # 8. 總結建議
    print("="*80)
    print("💡 總結與建議:")
    print("="*80)
    print("""
1. ✅ 自動提取了 {count} 個分類的商品範例
2. ⚠️  建議手動補充以下分類:
   - 「烹調食材」→ 應明確標註: 木茸、香菇、黑木耳、白木耳、海帶芽
   - 「醬油/味噌/糖」→ 應明確標註: 昆布醬油、黑豆蔭油、有機素蠔油
   - 「米類」→ 應明確標註: 有機白米、有機糙米、有機香米

3. 📊 商品數量 Top 3 分類:
   - 這些分類應優先顯示在 Prompt 中

4. 🚀 下一步:
   - 選擇方案 C: 自動生成 + 手動補充
   - 將生成的代碼整合到 llm_service.py
   - 重點加強「木茸」等容易誤判的商品

是否立即實施優化? (Y/N)
    """.format(count=len(examples)))

if __name__ == "__main__":
    main()

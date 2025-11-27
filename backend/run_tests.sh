#!/bin/bash
# -*- coding: utf-8 -*-
################################################################################
# CompanyResponseFormatter 測試啟動腳本
################################################################################
# 執行方式: ./run_tests.sh [選項]
# 選項:
#   interactive  - 執行互動式測試
#   unit         - 執行單元測試
#   built-in     - 執行內建測試
#   all          - 執行所有測試
#   (無參數)     - 顯示選單
################################################################################

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 切換到 script 所在目錄
cd "$(dirname "$0")"

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  CompanyResponseFormatter 測試工具${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# 函數: 互動式測試
run_interactive() {
    echo -e "\n${YELLOW}▶ 啟動互動式測試...${NC}\n"
    python3 test_formatter_interactive.py
}

# 函數: 單元測試
run_unit_tests() {
    echo -e "\n${YELLOW}▶ 執行單元測試...${NC}\n"
    
    # 檢查是否安裝 pytest
    if python3 -c "import pytest" 2>/dev/null; then
        echo -e "${GREEN}✓ 使用 pytest 執行測試${NC}"
        pytest tests/test_company_response_formatter.py -v --tb=short
    else
        echo -e "${YELLOW}! pytest 未安裝，使用標準測試模式${NC}"
        python3 tests/test_company_response_formatter.py
    fi
}

# 函數: 內建測試
run_builtin_tests() {
    echo -e "\n${YELLOW}▶ 執行內建測試...${NC}\n"
    python3 company_response_formatter.py
}

# 函數: 語法檢查
run_syntax_check() {
    echo -e "\n${YELLOW}▶ 執行語法檢查...${NC}\n"
    if python3 -m py_compile company_response_formatter.py; then
        echo -e "${GREEN}✓ 語法檢查通過${NC}"
        return 0
    else
        echo -e "${RED}✗ 語法檢查失敗${NC}"
        return 1
    fi
}

# 函數: 所有測試
run_all_tests() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  執行完整測試套件${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    
    # 1. 語法檢查
    echo -e "\n${YELLOW}【1/3】語法檢查${NC}"
    run_syntax_check || exit 1
    
    # 2. 單元測試
    echo -e "\n${YELLOW}【2/3】單元測試${NC}"
    run_unit_tests
    
    # 3. 內建測試
    echo -e "\n${YELLOW}【3/3】內建測試${NC}"
    run_builtin_tests
    
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ 所有測試完成！${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
}

# 函數: 顯示選單
show_menu() {
    echo ""
    echo -e "${YELLOW}請選擇測試模式:${NC}"
    echo "  1) 互動式測試 (推薦新手)"
    echo "  2) 單元測試 (推薦開發者)"
    echo "  3) 內建測試"
    echo "  4) 執行所有測試"
    echo "  5) 語法檢查"
    echo "  0) 離開"
    echo ""
    read -p "請輸入選項 (0-5): " choice
    
    case $choice in
        1)
            run_interactive
            ;;
        2)
            run_unit_tests
            ;;
        3)
            run_builtin_tests
            ;;
        4)
            run_all_tests
            ;;
        5)
            run_syntax_check
            ;;
        0)
            echo -e "\n${GREEN}👋 再見！${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}✗ 無效的選項${NC}"
            show_menu
            ;;
    esac
}

# 主程式邏輯
case "${1:-menu}" in
    interactive|i)
        run_interactive
        ;;
    unit|u)
        run_unit_tests
        ;;
    built-in|builtin|b)
        run_builtin_tests
        ;;
    all|a)
        run_all_tests
        ;;
    syntax|check|c)
        run_syntax_check
        ;;
    menu|m|"")
        show_menu
        ;;
    help|h|-h|--help)
        echo ""
        echo "使用方式: $0 [選項]"
        echo ""
        echo "選項:"
        echo "  interactive, i   執行互動式測試"
        echo "  unit, u          執行單元測試"
        echo "  built-in, b      執行內建測試"
        echo "  all, a           執行所有測試"
        echo "  syntax, c        語法檢查"
        echo "  help, h          顯示此說明"
        echo "  (無參數)         顯示選單"
        echo ""
        echo "範例:"
        echo "  $0 interactive   # 執行互動式測試"
        echo "  $0 all           # 執行所有測試"
        echo ""
        ;;
    *)
        echo -e "${RED}✗ 未知的選項: $1${NC}"
        echo "使用 '$0 help' 查看說明"
        exit 1
        ;;
esac

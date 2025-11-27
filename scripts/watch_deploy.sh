#!/bin/bash

# 檔案監控自動部署腳本 - SEARCH_Goods
# 功能：監控專案檔案變更，自動觸發部署
# 依賴：fswatch (macOS) 或 inotify-tools (Linux)
# 作者：GitHub Copilot

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
WATCH_DIRS=("backend" "frontend" "data" "docs")
IGNORE_PATTERNS=("*.pyc" "*.log" ".DS_Store" "node_modules" ".git" "__pycache__" "*.tmp")
DEPLOY_SCRIPT="./scripts/auto_deploy.sh"
DEBOUNCE_TIME=5  # 秒，避免頻繁觸發

log_info() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')]${NC} $1"
}

# 檢查依賴
check_dependencies() {
    if command -v fswatch >/dev/null 2>&1; then
        WATCHER="fswatch"
        log_info "使用 fswatch 監控檔案變更"
    elif command -v inotifywait >/dev/null 2>&1; then
        WATCHER="inotifywait"
        log_info "使用 inotifywait 監控檔案變更"
    else
        log_error "錯誤：需要安裝 fswatch (macOS) 或 inotify-tools (Linux)"
        echo "macOS 安裝: brew install fswatch"
        echo "Ubuntu 安裝: sudo apt-get install inotify-tools"
        exit 1
    fi
}

# 檢查部署腳本
check_deploy_script() {
    if [[ ! -f "$DEPLOY_SCRIPT" ]]; then
        log_error "錯誤：找不到部署腳本 $DEPLOY_SCRIPT"
        exit 1
    fi
    
    if [[ ! -x "$DEPLOY_SCRIPT" ]]; then
        log_info "設置部署腳本執行權限..."
        chmod +x "$DEPLOY_SCRIPT"
    fi
}

# 檢查是否應該忽略檔案
should_ignore() {
    local file="$1"
    for pattern in "${IGNORE_PATTERNS[@]}"; do
        if [[ "$file" == *"$pattern"* ]]; then
            return 0  # 應該忽略
        fi
    done
    return 1  # 不應該忽略
}

# 執行部署
trigger_deployment() {
    local changed_file="$1"
    
    log_info "檔案變更檢測: $changed_file"
    
    if should_ignore "$changed_file"; then
        log_info "忽略檔案: $changed_file"
        return
    fi
    
    log_warning "觸發自動部署..."
    
    # 等待一下，避免連續變更造成多次觸發
    sleep "$DEBOUNCE_TIME"
    
    # 執行部署腳本
    if "$DEPLOY_SCRIPT" -m "auto: file change detected in $changed_file"; then
        log_success "✅ 自動部署完成"
    else
        log_error "❌ 自動部署失敗"
    fi
    
    echo "----------------------------------------"
}

# 使用 fswatch 監控 (macOS)
watch_with_fswatch() {
    local watch_paths=""
    for dir in "${WATCH_DIRS[@]}"; do
        if [[ -d "$dir" ]]; then
            watch_paths="$watch_paths $dir"
        fi
    done
    
    if [[ -z "$watch_paths" ]]; then
        log_error "錯誤：沒有找到可監控的目錄"
        exit 1
    fi
    
    log_info "開始監控目錄: $watch_paths"
    log_info "忽略模式: ${IGNORE_PATTERNS[*]}"
    log_info "按 Ctrl+C 停止監控"
    echo "----------------------------------------"
    
    fswatch -o $watch_paths | while read num; do
        # 獲取最近變更的檔案
        local changed_file=$(find $watch_paths -type f -newer /tmp/fswatch_marker 2>/dev/null | head -1)
        touch /tmp/fswatch_marker
        
        if [[ -n "$changed_file" ]]; then
            trigger_deployment "$changed_file"
        fi
    done
}

# 使用 inotifywait 監控 (Linux)
watch_with_inotifywait() {
    local watch_paths=""
    for dir in "${WATCH_DIRS[@]}"; do
        if [[ -d "$dir" ]]; then
            watch_paths="$watch_paths $dir"
        fi
    done
    
    if [[ -z "$watch_paths" ]]; then
        log_error "錯誤：沒有找到可監控的目錄"
        exit 1
    fi
    
    log_info "開始監控目錄: $watch_paths"
    log_info "忽略模式: ${IGNORE_PATTERNS[*]}"
    log_info "按 Ctrl+C 停止監控"
    echo "----------------------------------------"
    
    inotifywait -m -r -e modify,create,delete,move $watch_paths --format '%w%f' | \
    while read changed_file; do
        trigger_deployment "$changed_file"
    done
}

# 清理函數
cleanup() {
    log_info "停止檔案監控..."
    exit 0
}

# 設置信號處理
trap cleanup SIGINT SIGTERM

# 主函數
main() {
    echo "🔍 SEARCH_Goods 檔案監控自動部署"
    echo "時間: $(date)"
    echo "目錄: $(pwd)"
    echo

    # 解析命令列參數
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--debounce)
                DEBOUNCE_TIME="$2"
                shift 2
                ;;
            -h|--help)
                echo "用法: $0 [選項]"
                echo "選項:"
                echo "  -d, --debounce TIME  防抖時間（秒，預設: 5）"
                echo "  -h, --help           顯示此說明"
                echo
                echo "監控目錄: ${WATCH_DIRS[*]}"
                echo "忽略模式: ${IGNORE_PATTERNS[*]}"
                exit 0
                ;;
            *)
                log_error "未知參數: $1"
                exit 1
                ;;
        esac
    done

    check_dependencies
    check_deploy_script
    
    # 創建標記檔案（用於 fswatch）
    touch /tmp/fswatch_marker
    
    # 根據可用的工具選擇監控方式
    case "$WATCHER" in
        "fswatch")
            watch_with_fswatch
            ;;
        "inotifywait")
            watch_with_inotifywait
            ;;
        *)
            log_error "未知的監控工具: $WATCHER"
            exit 1
            ;;
    esac
}

# 執行主函數
main "$@"
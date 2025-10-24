#!/bin/bash

# 自動部署腳本 - SEARCH_Goods
# 功能：檢測程式碼變更，自動提交到 GitHub 並觸發 Render/Netlify 部署
# 作者：GitHub Copilot
# 日期：$(date +%Y-%m-%d)

set -e  # 遇到錯誤時退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 檢查是否在正確的專案目錄
check_project_directory() {
    if [[ ! -f "package.json" && ! -f "backend/requirements.txt" ]]; then
        log_error "錯誤：請在 SEARCH_Goods 專案根目錄執行此腳本"
        exit 1
    fi
    log_info "✓ 專案目錄確認"
}

# 檢查 Git 狀態
check_git_status() {
    if ! git status &>/dev/null; then
        log_error "錯誤：此目錄不是 Git 倉庫"
        exit 1
    fi
    
    # 檢查是否有未提交的變更
    if git diff-index --quiet HEAD --; then
        log_warning "沒有檢測到程式碼變更"
        return 1
    else
        log_info "✓ 檢測到程式碼變更"
        return 0
    fi
}

# 顯示變更的檔案
show_changes() {
    log_info "變更的檔案："
    git status --porcelain | while read -r line; do
        echo "  $line"
    done
    echo
}

# 執行測試（可選）
run_tests() {
    if [[ "$SKIP_TESTS" != "true" ]]; then
        log_info "執行後端測試..."
        if [[ -d "backend" && -f "backend/requirements.txt" ]]; then
            cd backend
            if python -m pytest -q 2>/dev/null; then
                log_success "✓ 測試通過"
            else
                log_warning "⚠ 測試失敗，但繼續部署（使用 SKIP_TESTS=true 跳過測試）"
            fi
            cd ..
        fi
    else
        log_info "跳過測試（SKIP_TESTS=true）"
    fi
}

# 提交變更到 Git
commit_changes() {
    local commit_message="${1:-"chore: auto deployment - $(date '+%Y-%m-%d %H:%M:%S')"}"
    
    log_info "添加所有變更到暫存區..."
    git add .
    
    log_info "提交變更..."
    git commit -m "$commit_message"
    log_success "✓ 變更已提交"
}

# 推送到 GitHub
push_to_github() {
    local branch="${1:-main}"
    
    log_info "推送到 GitHub ($branch 分支)..."
    if git push origin "$branch"; then
        log_success "✓ 成功推送到 GitHub"
    else
        log_error "推送失敗"
        exit 1
    fi
}

# 等待並監控部署狀態
monitor_deployment() {
    local repo="jacky6063/SEARCH_Goods"
    local max_wait=300  # 5分鐘超時
    local wait_time=0
    
    log_info "監控 GitHub Actions 部署狀態..."
    
    while [[ $wait_time -lt $max_wait ]]; do
        # 檢查最新的工作流程運行狀態
        local status=$(curl -s "https://api.github.com/repos/$repo/actions/runs?per_page=1" | \
                      grep -o '"status":"[^"]*"' | \
                      head -1 | \
                      cut -d'"' -f4)
        
        local conclusion=$(curl -s "https://api.github.com/repos/$repo/actions/runs?per_page=1" | \
                          grep -o '"conclusion":"[^"]*"' | \
                          head -1 | \
                          cut -d'"' -f4)
        
        case "$status" in
            "queued")
                echo -n "⏳ 等待中..."
                ;;
            "in_progress")
                echo -n "🔄 部署中..."
                ;;
            "completed")
                if [[ "$conclusion" == "success" ]]; then
                    log_success "✅ 部署成功完成！"
                    return 0
                else
                    log_error "❌ 部署失敗 (conclusion: $conclusion)"
                    return 1
                fi
                ;;
            *)
                echo -n "❓ 未知狀態: $status..."
                ;;
        esac
        
        sleep 10
        wait_time=$((wait_time + 10))
        echo " (${wait_time}s)"
    done
    
    log_warning "⏰ 監控超時（5分鐘），請手動檢查部署狀態"
    echo "GitHub Actions: https://github.com/$repo/actions"
}

# 顯示部署連結
show_deployment_links() {
    log_info "部署連結："
    echo "📊 GitHub Actions: https://github.com/jacky6063/SEARCH_Goods/actions"
    echo "🚀 Render 控制台: https://dashboard.render.com/"
    echo "🌐 Netlify 控制台: https://app.netlify.com/"
}

# 主函數
main() {
    log_info "🚀 SEARCH_Goods 自動部署腳本啟動"
    echo "時間: $(date)"
    echo "目錄: $(pwd)"
    echo

    # 解析命令列參數
    local commit_message=""
    local branch="main"
    local force_deploy=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--message)
                commit_message="$2"
                shift 2
                ;;
            -b|--branch)
                branch="$2"
                shift 2
                ;;
            -f|--force)
                force_deploy=true
                shift
                ;;
            -h|--help)
                echo "用法: $0 [選項]"
                echo "選項:"
                echo "  -m, --message MSG    自訂提交訊息"
                echo "  -b, --branch BRANCH  指定分支 (預設: main)"
                echo "  -f, --force          強制部署（即使沒有變更）"
                echo "  -h, --help           顯示此說明"
                echo
                echo "環境變數:"
                echo "  SKIP_TESTS=true      跳過測試執行"
                exit 0
                ;;
            *)
                log_error "未知參數: $1"
                exit 1
                ;;
        esac
    done

    # 執行部署流程
    check_project_directory
    
    if check_git_status || [[ "$force_deploy" == "true" ]]; then
        if [[ "$force_deploy" == "true" && -z "$(git status --porcelain)" ]]; then
            log_info "強制部署模式：創建空提交"
            git commit --allow-empty -m "${commit_message:-"chore: force deployment - $(date '+%Y-%m-%d %H:%M:%S')"}"
        else
            show_changes
            run_tests
            commit_changes "$commit_message"
        fi
        
        push_to_github "$branch"
        
        echo
        log_success "🎉 部署已觸發！"
        show_deployment_links
        
        # 可選：監控部署狀態
        if [[ "${MONITOR_DEPLOYMENT:-true}" == "true" ]]; then
            echo
            monitor_deployment
        fi
        
    else
        log_info "沒有變更需要部署"
        exit 0
    fi
}

# 執行主函數
main "$@"
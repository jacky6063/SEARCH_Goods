#!/bin/bash

# 環境設置腳本 - SEARCH_Goods
# 功能：安裝依賴並設置開發環境
# 作者：GitHub Copilot

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 檢測作業系統
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log_info "檢測到 macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        log_info "檢測到 Linux"
    else
        log_error "不支援的作業系統: $OSTYPE"
        exit 1
    fi
}

# 安裝 fswatch (macOS) 或 inotify-tools (Linux)
install_file_watcher() {
    log_info "安裝檔案監控工具..."
    
    case "$OS" in
        "macos")
            if ! command -v fswatch >/dev/null 2>&1; then
                if command -v brew >/dev/null 2>&1; then
                    brew install fswatch
                    log_success "✓ fswatch 安裝完成"
                else
                    log_error "請先安裝 Homebrew: https://brew.sh"
                    exit 1
                fi
            else
                log_success "✓ fswatch 已安裝"
            fi
            ;;
        "linux")
            if ! command -v inotifywait >/dev/null 2>&1; then
                if command -v apt-get >/dev/null 2>&1; then
                    sudo apt-get update
                    sudo apt-get install -y inotify-tools
                elif command -v yum >/dev/null 2>&1; then
                    sudo yum install -y inotify-tools
                elif command -v dnf >/dev/null 2>&1; then
                    sudo dnf install -y inotify-tools
                else
                    log_error "無法檢測包管理器，請手動安裝 inotify-tools"
                    exit 1
                fi
                log_success "✓ inotify-tools 安裝完成"
            else
                log_success "✓ inotify-tools 已安裝"
            fi
            ;;
    esac
}

# 設置腳本執行權限
setup_script_permissions() {
    log_info "設置腳本執行權限..."
    
    local scripts=("scripts/auto_deploy.sh" "scripts/watch_deploy.sh" "scripts/setup.sh")
    
    for script in "${scripts[@]}"; do
        if [[ -f "$script" ]]; then
            chmod +x "$script"
            log_success "✓ $script 權限已設置"
        fi
    done
}

# 安裝 Python 依賴
install_python_deps() {
    log_info "檢查 Python 環境..."
    
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "請先安裝 Python 3"
        exit 1
    fi
    
    log_success "✓ Python 3 已安裝 ($(python3 --version))"
    
    if [[ -d "backend" && -f "backend/requirements.txt" ]]; then
        log_info "安裝後端 Python 依賴..."
        cd backend
        
        # 創建虛擬環境（如果不存在）
        if [[ ! -d ".venv" ]]; then
            python3 -m venv .venv
            log_success "✓ 虛擬環境已創建"
        fi
        
        # 啟用虛擬環境並安裝依賴
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        log_success "✓ 後端依賴安裝完成"
        
        cd ..
    fi
}

# 檢查 Git 配置
check_git_config() {
    log_info "檢查 Git 配置..."
    
    if ! command -v git >/dev/null 2>&1; then
        log_error "請先安裝 Git"
        exit 1
    fi
    
    if [[ -z "$(git config user.name)" || -z "$(git config user.email)" ]]; then
        log_warning "Git 用戶信息未設置"
        echo "請執行以下命令設置 Git 用戶信息："
        echo "git config --global user.name \"Your Name\""
        echo "git config --global user.email \"your.email@example.com\""
    else
        log_success "✓ Git 配置正常"
    fi
}

# 創建環境配置檔案
create_env_files() {
    log_info "創建環境配置檔案..."
    
    if [[ -f "backend/.env.example" && ! -f "backend/.env" ]]; then
        cp "backend/.env.example" "backend/.env"
        log_success "✓ 後端 .env 檔案已創建"
        log_warning "請編輯 backend/.env 設置必要的環境變數"
    fi
}

# 顯示使用說明
show_usage() {
    echo
    log_success "🎉 設置完成！"
    echo
    echo "可用的命令："
    echo "📦 npm run deploy          - 手動部署"
    echo "🚀 npm run deploy:force    - 強制部署"
    echo "👀 npm run deploy:watch    - 啟動檔案監控自動部署"
    echo "🧪 npm run test            - 執行測試"
    echo "🔧 npm run start:backend   - 啟動後端服務"
    echo "🌐 npm run start:frontend  - 啟動前端服務"
    echo "🐳 npm run docker:dev      - Docker 開發環境"
    echo
    echo "或直接使用腳本："
    echo "./scripts/auto_deploy.sh -h      - 查看部署腳本說明"
    echo "./scripts/watch_deploy.sh -h     - 查看監控腳本說明"
    echo
    echo "開始開發："
    echo "1. 編輯 backend/.env 設置環境變數"
    echo "2. 執行 npm run start:backend 啟動後端"
    echo "3. 執行 npm run start:frontend 啟動前端"
    echo "4. 執行 npm run deploy:watch 啟動自動部署監控"
}

# 主函數
main() {
    echo "🚀 SEARCH_Goods 環境設置"
    echo "時間: $(date)"
    echo

    detect_os
    install_file_watcher
    setup_script_permissions
    install_python_deps
    check_git_config
    create_env_files
    show_usage
}

# 執行主函數
main "$@"
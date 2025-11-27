#!/bin/bash
# =====================================================
# 快速測試腳本
# =====================================================
# 用途：快速執行單一測試套件
# 使用：
#   ./scripts/quick_test.sh e2e      # E2E 測試
#   ./scripts/quick_test.sh backend  # 後端測試
#   ./scripts/quick_test.sh all      # 全部測試
# =====================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

TEST_TYPE=${1:-all}

case $TEST_TYPE in
    e2e)
        log_info "執行 E2E 測試..."
        npm run test:e2e
        ;;
    backend)
        log_info "執行後端測試..."
        cd backend
        source .venv/bin/activate 2>/dev/null || true
        pytest -v --tb=short
        ;;
    all)
        log_info "執行所有測試..."
        
        log_info "1/2 後端測試"
        cd backend
        source .venv/bin/activate 2>/dev/null || true
        pytest -v --tb=short
        cd ..
        
        log_info "2/2 E2E 測試"
        npm run test:e2e
        
        log_success "所有測試完成"
        ;;
    *)
        log_error "未知的測試類型: $TEST_TYPE"
        echo "使用方式："
        echo "  $0 e2e      # E2E 測試"
        echo "  $0 backend  # 後端測試"
        echo "  $0 all      # 全部測試"
        exit 1
        ;;
esac

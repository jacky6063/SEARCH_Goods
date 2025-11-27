#!/usr/bin/env python3
"""
檢查生產環境前端版本
"""
import sys
import requests
from bs4 import BeautifulSoup

def check_frontend_version(url):
    """檢查前端版本"""
    print("="*60)
    print(f"🔍 檢查前端版本: {url}")
    print("="*60)
    
    try:
        # 加入 cache-busting 參數
        import time
        cache_buster = int(time.time())
        response = requests.get(f"{url}?_={cache_buster}", timeout=10, headers={
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        if response.status_code != 200:
            print(f"❌ HTTP 錯誤: {response.status_code}")
            return False
        
        html = response.text
        
        # 檢查快取版本
        if '2025-11-09-rich-content-v1' in html:
            print("✅ 前端版本: 最新 (2025-11-09-rich-content-v1)")
            print("   包含可點擊連結功能")
        elif '2025-11-04' in html:
            print("❌ 前端版本: 舊版 (2025-11-04-v2)")
            print("   沒有可點擊連結功能")
            print("")
            print("⚠️ 生產環境尚未更新！")
            return False
        else:
            print("⚠️ 無法辨識前端版本")
            print("   搜尋 'Cache buster' 註解...")
            if 'Cache buster:' in html:
                import re
                match = re.search(r'Cache buster: ([^\s]+)', html)
                if match:
                    print(f"   找到: {match.group(1)}")
        
        # 檢查關鍵函數
        print("\n📝 檢查關鍵程式碼:")
        
        checks = [
            ('appendChatBubble', 'richContent = null', '可點擊連結渲染函數'),
            ('rich-content-container', 'rich-content-container', '豐富內容容器'),
            ('DEBUG', '[DEBUG]', '調試日誌'),
            ('Google Maps', 'google.com/maps', 'Google Maps 整合'),
        ]
        
        all_passed = True
        for name, pattern, desc in checks:
            if pattern in html:
                print(f"  ✅ {name}: {desc}")
            else:
                print(f"  ❌ {name}: 缺少 {desc}")
                all_passed = False
        
        if all_passed:
            print("\n✅ 所有功能檢查通過")
            print("\n💡 如果瀏覽器仍顯示舊版，請:")
            print("   1. 清除瀏覽器快取")
            print("   2. 完全關閉瀏覽器後重開")
            print("   3. 使用無痕模式測試")
            return True
        else:
            print("\n❌ 部分功能缺失，生產環境可能尚未更新")
            return False
            
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False

def main():
    # 檢查生產環境 URL
    production_urls = [
        "https://search-goods.netlify.app",  # 預設 Netlify URL
        # 如果有自訂域名，加在這裡
    ]
    
    print("\n🌐 檢查生產環境前端版本\n")
    
    if len(sys.argv) > 1:
        production_urls = [sys.argv[1]]
    
    results = []
    for url in production_urls:
        result = check_frontend_version(url)
        results.append((url, result))
        print()
    
    print("="*60)
    print("📊 檢查總結")
    print("="*60)
    
    all_updated = all(result for _, result in results)
    
    if all_updated:
        print("✅ 所有環境已更新到最新版本")
        print("\n🎉 可以開始測試可點擊連結功能了！")
        print("\n測試步驟:")
        print("1. 開啟生產環境網站")
        print("2. 清除瀏覽器快取 (Cmd+Shift+Delete)")
        print("3. 重新載入頁面 (Cmd+Shift+R)")
        print("4. 輸入「公司電話是多少？」")
        print("5. 應該看到可點擊的按鈕")
    else:
        print("❌ 部分環境尚未更新")
        print("\n可能原因:")
        print("1. 前端尚未部署到 Netlify")
        print("2. CDN 快取尚未更新 (需要 5-10 分鐘)")
        print("3. 需要手動觸發 Netlify 部署")
        print("\n建議動作:")
        print("1. 執行 ./deploy_frontend.sh 手動部署")
        print("2. 或等待 10 分鐘讓 CDN 更新")
        print("3. 或在 Netlify Dashboard 手動觸發部署")

if __name__ == "__main__":
    main()

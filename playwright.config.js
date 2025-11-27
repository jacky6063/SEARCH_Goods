const { defineConfig, devices } = require('@playwright/test');

/**
 * Playwright 配置文件
 * 設定測試環境和執行參數
 */

module.exports = defineConfig({
  // 測試文件位置
  testDir: './tests/e2e',
  
  // 測試超時時間（30 秒）
  timeout: 30 * 1000,
  
  // 每個測試的重試次數
  retries: 2,
  
  // 並行執行的 worker 數量
  workers: 1,
  
  // 測試報告格式
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list']
  ],
  
  // 共用設定
  use: {
    // 基礎 URL
    baseURL: 'http://localhost:5173',
    
    // 瀏覽器選項
    headless: true,  // 無頭模式（背景執行）
    
    // 截圖設定
    screenshot: 'only-on-failure',  // 失敗時截圖
    
    // 錄影設定
    video: 'retain-on-failure',  // 失敗時保留錄影
    
    // 追蹤設定（用於除錯）
    trace: 'on-first-retry',
  },
  
  // 測試專案（瀏覽器）
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  
  // Web Server 設定（測試前自動啟動）
  webServer: [
    {
      command: 'cd backend && python3 -m uvicorn app:app --host 0.0.0.0 --port 8000',
      port: 8000,
      timeout: 120 * 1000,
      reuseExistingServer: true,
    },
    {
      command: 'cd frontend && python3 -m http.server 5173',
      port: 5173,
      timeout: 120 * 1000,
      reuseExistingServer: true,
    },
  ],
});

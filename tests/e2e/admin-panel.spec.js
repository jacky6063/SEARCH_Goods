const { test, expect } = require('@playwright/test');

/**
 * 管理面板功能測試
 * 這些測試會檢查管理面板的所有核心功能
 */

test.describe('管理面板基本功能', () => {
  test.beforeEach(async ({ page }) => {
    // 每個測試前都先打開首頁
    await page.goto('http://localhost:5173');
  });

  test('應該能打開和關閉管理面板', async ({ page }) => {
    // 點擊管理按鈕
    await page.click('#adminToggle');
    
    // 確認面板顯示
    await expect(page.locator('#adminPanel')).toBeVisible();
    
    // 點擊關閉按鈕
    await page.click('#adminPanelClose');
    
    // 確認面板隱藏
    await expect(page.locator('#adminPanel')).toBeHidden();
  });

  test('應該顯示正確的管理端點 URL', async ({ page }) => {
    // 點擊管理按鈕
    await page.click('#adminToggle');
    
    // 等待面板顯示
    await page.waitForSelector('#adminPanel', { state: 'visible' });
    
    // 檢查上傳 CSV 的 URL
    const uploadUrl = await page.locator('#adminUrlUpload').textContent();
    expect(uploadUrl).toContain('/api/admin/upload-csv');
    expect(uploadUrl).not.toBe('undefined/api/admin/upload-csv');
    
    // 檢查清除快取的 URL
    const clearUrl = await page.locator('#adminUrlClear').textContent();
    expect(clearUrl).toContain('/api/admin/clear-cache');
    expect(clearUrl).not.toBe('undefined/api/admin/clear-cache');
  });

  test('buildAdminEndpoint 函數應該正確運作', async ({ page }) => {
    // 監聽 JavaScript 錯誤
    const errors = [];
    page.on('pageerror', error => {
      errors.push(error.message);
      console.error('❌ JavaScript Error:', error.message);
    });
    
    // 打開管理面板
    await page.click('#adminToggle');
    await page.waitForSelector('#adminPanel', { state: 'visible' });
    
    // 確認沒有 "buildAdminEndpoint is not defined" 錯誤
    const hasUndefinedError = errors.some(err => 
      err.includes('buildAdminEndpoint') && err.includes('not defined')
    );
    expect(hasUndefinedError).toBe(false);
    
    // 確認 URL 正確顯示
    const uploadUrl = await page.locator('#adminUrlUpload').textContent();
    expect(uploadUrl).toMatch(/^https?:\/\/.+\/api\/admin\/upload-csv$/);
  });

  test('應該能設定 API 端點', async ({ page }) => {
    // 打開管理面板
    await page.click('#adminToggle');
    
    // 輸入 API 端點
    await page.fill('#adminApiEndpoint', 'http://localhost:8000/api/search');
    
    // 點擊「設為 API」按鈕
    await page.click('#adminSetApi');
    
    // 等待狀態訊息
    await page.waitForTimeout(500);
    
    // 確認顯示成功訊息
    const statusMsg = await page.locator('#adminMsg').textContent();
    expect(statusMsg).toContain('已更新');
  });
});

test.describe('管理面板 - 參數設定', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173');
    await page.click('#adminToggle');
    await page.waitForSelector('#adminPanel', { state: 'visible' });
  });

  test('應該能輸入 Logo URL', async ({ page }) => {
    const testUrl = 'https://example.com/logo.png';
    
    // 輸入 Logo URL
    await page.fill('#logoUrlInput', testUrl);
    
    // 確認輸入成功
    const value = await page.inputValue('#logoUrlInput');
    expect(value).toBe(testUrl);
  });

  test('應該能輸入 YouTube URL', async ({ page }) => {
    const testUrl = 'https://youtu.be/dQw4w9WgXcQ';
    
    // 輸入 YouTube URL
    await page.fill('#youtubeUrlInput', testUrl);
    
    // 確認輸入成功
    const value = await page.inputValue('#youtubeUrlInput');
    expect(value).toBe(testUrl);
  });

  test('應該能切換語音模式開關', async ({ page }) => {
    // 取得語音模式開關
    const voiceToggle = page.locator('#voiceModeToggle');
    
    // 確認開關存在
    await expect(voiceToggle).toBeVisible();
    
    // 取得初始狀態
    const initialState = await voiceToggle.isChecked();
    
    // 切換開關
    await voiceToggle.click();
    
    // 確認狀態改變
    const newState = await voiceToggle.isChecked();
    expect(newState).toBe(!initialState);
  });

  test('清除按鈕應該清空所有輸入', async ({ page }) => {
    // 填入測試資料
    await page.fill('#logoUrlInput', 'https://example.com/logo.png');
    await page.fill('#youtubeUrlInput', 'https://youtu.be/test');
    await page.fill('#promptInput', '測試提示詞');
    
    // 點擊清除按鈕
    await page.click('#clearParamsBtn');
    
    // 等待清除完成
    await page.waitForTimeout(500);
    
    // 確認所有欄位已清空
    expect(await page.inputValue('#logoUrlInput')).toBe('');
    expect(await page.inputValue('#youtubeUrlInput')).toBe('');
    expect(await page.inputValue('#promptInput')).toBe('');
  });
});

test.describe('錯誤檢測', () => {
  test('頁面應該沒有 JavaScript 錯誤', async ({ page }) => {
    const errors = [];
    const warnings = [];
    
    // 監聽所有 console 訊息
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      } else if (msg.type() === 'warning') {
        warnings.push(msg.text());
      }
    });
    
    // 監聽 JavaScript 錯誤
    page.on('pageerror', error => {
      errors.push(error.message);
    });
    
    // 載入頁面
    await page.goto('http://localhost:5173');
    
    // 打開管理面板
    await page.click('#adminToggle');
    await page.waitForSelector('#adminPanel', { state: 'visible' });
    
    // 點擊各種按鈕測試
    await page.click('#adminSetApi');
    await page.waitForTimeout(300);
    
    // 輸出錯誤（如果有）
    if (errors.length > 0) {
      console.error('發現 JavaScript 錯誤:', errors);
    }
    
    // 確認沒有嚴重錯誤
    expect(errors.length).toBe(0);
  });
});

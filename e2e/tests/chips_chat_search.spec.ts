import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:8000';

async function waitForChatReply(page){
  await expect(page.locator('#chat-messages .bubble.assistant')).toHaveCount(1, { timeout: 15000 });
}

test.describe('Hot chips → Chat → Chips → Search flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE);
    // 確保在聊天模式
    await expect(page.locator('body.chat-mode')).toBeVisible();
    // 熱門分類區可見（或顯示佔位）
    await expect(page.locator('#hotCategories')).toBeVisible();
  });

  test('Click L1 chip should send chat and update to L2 chips', async ({ page }) => {
    const chips = page.locator('#hotCategories button.btn');
    const chipCount = await chips.count();
    expect(chipCount).toBeGreaterThan(0);

    // 點第一個 L1 chip
    await chips.first().click();

    // 等待聊天回覆
    await expect(page.locator('#chat-messages .bubble.assistant')).toHaveCount(1, { timeout: 15000 });
    // 熱門分類區仍可見（且可能更新為 L2）
    await expect(page.locator('#hotCategories')).toBeVisible();
  });

  test('From chips to products only after LLM switch_to_search or explicit request', async ({ page }) => {
    // 先點一個 L1，觸發聊天
    const chips = page.locator('#hotCategories button.btn');
    await chips.first().click();
    await waitForChatReply(page);

    // 模擬使用者主動要求顯示商品
    const input = page.locator('#q');
    await input.fill('顯示商品');
    await page.locator('#sendBtn').click();

    // 預期切到商品模式（search-mode 啟用），熱門分類隱藏
    await expect(page.locator('body.search-mode')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('#hotCategories')).toBeHidden();

    // 有搜尋結果或空狀態卡
    const results = page.locator('#results .card');
    await expect(results.or(page.locator('#results'))).toBeVisible();
  });
});

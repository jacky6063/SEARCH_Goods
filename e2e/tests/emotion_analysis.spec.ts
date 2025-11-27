import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('repair_chat_viewer emotion integration', () => {
  test('renders emotion badges and filters high-risk messages', async ({ page }) => {
    const filePath = 'file://' + path.join(__dirname, '../../frontend/repair_chat_viewer.html');
    const targetDate = '2025-11-21';

    // 在頁面中覆寫 fetch，針對聊天查詢回傳假資料
    await page.addInitScript(({ mockDate }) => {
      const mockPayload = {
        total_count: 4,
        user_count: 2,
        llm_count: 2,
        session_count: 1,
        messages: [
          {
            message_id: 101,
            session_id: 'session-1',
            role: 'user',
            content: '瓦斯洩漏了！很危險！',
            created_at: `${mockDate}T10:00:00Z`,
            emotion_data: {
              anxiety_level: 9,
              urgency_level: 10,
              anger_level: 3,
              reasoning: '含緊急關鍵字',
            },
          },
          {
            message_id: 102,
            session_id: 'session-1',
            role: 'llm',
            content: '系統回覆',
            created_at: `${mockDate}T10:00:05Z`,
          },
          {
            message_id: 103,
            session_id: 'session-1',
            role: 'user',
            content: '冷氣保養什麼時候方便？',
            created_at: `${mockDate}T10:01:00Z`,
            emotion_data: {
              anxiety_level: 3,
              urgency_level: 4,
              anger_level: 2,
              reasoning: '語氣平和',
            },
          },
          {
            message_id: 104,
            session_id: 'session-1',
            role: 'llm',
            content: '回覆 OK',
            created_at: `${mockDate}T10:01:05Z`,
          },
        ],
      };

      const originalFetch = window.fetch;
      window.fetch = (input: RequestInfo, init?: RequestInit) => {
        if (typeof input === 'string' && input.includes('/api/repair/chat_logs')) {
          return Promise.resolve(
            new Response(JSON.stringify(mockPayload), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }),
          );
        }
        return originalFetch(input, init);
      };
    }, { mockDate: targetDate });

    await page.goto(filePath);

    await page.fill('#queryDate', targetDate);

    await page.click('.btn-search');
    await page.waitForSelector('.message-card.user', { timeout: 5000 });

    // 驗證徽章出現
    const badgeTexts = await page.$$eval('.message-card.user .emotion-badge', (els) =>
      els.map((el) => el.textContent?.trim() || '')
    );
    expect(badgeTexts.length).toBeGreaterThan(0);
    expect(badgeTexts.some((txt) => txt.includes('不安') || txt.includes('緊急'))).toBeTruthy();

    // 篩選高風險後，僅高情緒訊息顯示
    await page.selectOption('#emotionFilter', 'high');
    await page.waitForTimeout(150);

    const visibleCount = await page.$$eval('.message-card.user', (cards) =>
      cards.filter((card) => card.style.display !== 'none').length
    );
    expect(visibleCount).toBe(1);
  });
});

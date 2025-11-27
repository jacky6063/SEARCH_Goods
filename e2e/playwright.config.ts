import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // testDir 相對於本檔案所在目錄
  testDir: './tests',
  timeout: 60_000,
  fullyParallel: true,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8000',
    headless: true,
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ]
});

# 文件稽核決策紀錄（DOC_AUDIT_DECISIONS）

格式說明：
- path: 檔案路徑
- decision: keep | update | archive
- reason: 簡述原因（如：路由改動、部署管線更換等）
- replacement: 若 archive，請提供替代文件或入口（如：README.md 某段）
- last_reviewed: yyyy-mm-dd

---

- path: README.md
  decision: update
  reason: CI/CD 說明更新為 Render-only，移除 Netlify 依賴
  replacement: docs/archive/2025-11/ 下保留歷史 Netlify 文檔
  last_reviewed: 2025-11-17

- path: START_HERE.md
  decision: update
  reason: 啟動命令補上 --host 0.0.0.0，與現行後端一致
  replacement: 
  last_reviewed: 2025-11-17

- path: backend/README.md
  decision: update
  reason: 加註前端由 FastAPI 提供、Netlify 已停用
  replacement: 
  last_reviewed: 2025-11-17

- path: LOCAL_TEST_GUIDE.md
  decision: update
  reason: 前端本地訪問改為 http://localhost:8000；補正分類 scope 參數
  replacement: 
  last_reviewed: 2025-11-17

- path: docs/archive/2025-11/DEPLOYMENT_SETUP.md
  decision: archive
  reason: Netlify 時代部署指引，與現行 Render-only 流程不符
  replacement: DEPLOYMENT_CHECKLIST.md、README.md CI/CD 段落
  last_reviewed: 2025-11-17

- path: DEPLOYMENT_CHECKLIST.md
  decision: update
  reason: 明確為已驗證，並標註 Netlify 已停用
  replacement: 
  last_reviewed: 2025-11-17

- path: UPLOAD_TROUBLESHOOTING.md
  decision: keep
  reason: 與現行 Admin API / 清快取流程一致
  replacement: 
  last_reviewed: 2025-11-17

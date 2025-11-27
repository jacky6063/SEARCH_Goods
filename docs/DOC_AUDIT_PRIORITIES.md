# 文件稽核優先級清單（DOC_AUDIT_PRIORITIES）


目的：先處理最可能影響新人或使用者的入口與關鍵說明。

P0（立即複核與修正/歸檔決策）
- README.md（含 GitHub Actions、部署說明是否仍準確）
- START_HERE.md（若有實作步驟與現況不符需更新）
- backend/README.md（本機啟動、Admin API、環境變數）
- LOCAL_TEST_GUIDE.md（與最新本地啟動流程一致性）
- DEPLOYMENT_SETUP.md / DEPLOYMENT_CHECKLIST.md（與現行 Render 部署一致性）
- UPLOAD_TROUBLESHOOTING.md（Admin 上傳與快取清除流程）

P1（高優先，但不阻塞啟動）
- LLM_CHAT_SETUP.md、LLM_MANDATORY_MODE.md（旗標與模型對照）
- FRONTEND_MIGRATION_IMPLEMENTATION.md / EVALUATION.md 類（對應現行前端架構）
- 商品/分類/搜尋流程相關文件（FLOW_*、FILTER_BY_*、CATEGORY_*）

P2（一般）
- 歷史分析、測試報告、專案里程碑總結等

作業方式
- 逐檔對照程式碼與實機驗證，結果填入 DOC_AUDIT_DECISIONS.md

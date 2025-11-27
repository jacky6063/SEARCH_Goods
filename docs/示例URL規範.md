# 示例 URL 寫法規範

- 若文件需顯式標示 API URL，統一使用本機開發端點：
  - http://localhost:8000
  - 例：
    - GET http://localhost:8000/api/catalog/scope?level=L2&parent_l1=常溫食品
    - POST http://localhost:8000/api/search

- 若僅描述路徑（不需顯式域名），可保留 /api/...，但推薦顯式 URL 以避免混淆。

- 部署環境 URL（如 Render/Netlify）僅在部署/驗證文件中使用，不作為一般示例。

- 此規範適用於：
  - 說明文檔（FLOW_*、CATEGORY_*、FILTER_BY_*）
  - 快速參考卡、操作指南
  - 部署與驗證文件（保留部署域名除外）

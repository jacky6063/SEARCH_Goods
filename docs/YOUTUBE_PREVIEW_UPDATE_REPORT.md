# 聊天室 YouTube 點擊預覽改版報告

**更新日期**：2025-11-09  
**負責人**：Codex  
**版本**：`main@dff1235`

---

## 1. 緣由
- 使用者在聊天室收到含 YouTube 連結的推薦時，只能透過新分頁觀看，左側「品牌影音」區仍停留在預設影片，缺乏沉浸式體驗。
- 既有的播放器設定（管理面板輸入品牌影片 URL）必須保留，點擊聊天連結時不能破壞原本開新視窗的操作。

---

## 2. 調整重點
1. **沿用現有播放器邏輯**  
   - 沒有新增播放器，直接重用 `applyYoutube(url)` 函式，確保同樣支援各種 YouTube URL（標準、embed、shorts）。

2. **事件委派監聽**  
   - 在 `#chat-messages` 容器掛上 `click` 事件：只要偵測到 `<a>` 的 `href` 包含 `youtube.com` 或 `youtu.be`，即呼叫 `applyYoutube(href)` 更新 iframe。
   - 使用 `setTimeout(..., 0)` 觸發，避免干擾 `<a>` 原有的 `_blank` 開新分頁行為。

3. **狀態維持**  
   - 管理面板設定 (`_branding.youtube_url`) 依舊作為預設影片。使用者離開頁面或重新整理後，播放器會再次載入管理員指定的影片，不受聊天點擊影響。

---

## 3. 變更檔案
| 檔案 | 說明 |
|------|------|
| `frontend/index.html` | - 新增 `const chatMessagesEl` 事件監聽器<br>- 新增 `YOUTUBE_LINK_RE` 判斷<br>- 點擊聊天連結時呼叫 `applyYoutube` |

---

## 4. 測試紀錄
1. **本地手動測試**  
   - 管理面板設定品牌影片 → 頁面載入後左側正常自動播放。  
   - 聊天輸入關鍵字產生含 `https://youtu.be/...` 的回覆。  
   - 點擊聊天連結 → 新分頁開啟 YouTube，左側 iframe 立即切換至 clicked 影片。
2. **自動化測試**  
   - 目前無新增測試。建議後續以 Playwright 補強：模擬點擊聊天版面中的 YouTube 連結，驗證 iframe `src` 變化。

---

## 5. 待辦／建議
| 項目 | 說明 |
|------|------|
| 自動化測試 | 建議新增 E2E 測試，檢查點擊後 iframe `src` 是否變更。 |
| 使用者提示 | 考慮在品牌影音區塊加上小提示：「點聊天影片連結可於此預覽」。 |
| 操作歷史 | 若要保留使用者點擊歷史，可記錄最後一次聊天觸發的影片 URL，供重新整理時回復。 |

---

## 6. 版本資訊
- Commit：`dff1235`（2025-11-09）
- 受影響頁面：前端 SPA（`frontend/index.html`）
- 回溯方案：若需取消功能，移除 `chatMessagesEl.addEventListener('click', ...)` 區塊即可。


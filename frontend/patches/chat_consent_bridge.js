// == goods_1024001: 聊天同意詞橋接（優先 suggestion_ids） ==
export function installChatConsentBridge(getLastAssistantJson, getLastAssistantHtml, renderList) {
  const agreeLex = /^(要|OK|Ok|ok|好|可以|行|確定|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;

  async function onUserSend(text) {
    if (!agreeLex.test((text || "").trim())) return false;

    // 1) 優先用上一則助理 JSON 的 suggestion_ids
    let ids = [];
    try {
      const j = (typeof getLastAssistantJson === "function") ? getLastAssistantJson() : null;
      if (j && Array.isArray(j.suggestion_ids) && j.suggestion_ids.length) {
        ids = j.suggestion_ids.slice(0, 60);
      }
    } catch (e) {}

    // 2) 沒有的話，退而求其次從 HTML 抓 #471… 或 data-good-id
    if (!ids.length) {
      const html = (typeof getLastAssistantHtml === "function") ? getLastAssistantHtml() : "";
      const s = new Set();
      for (const m of html.matchAll(/#(\d{6,})/g)) s.add(String(m[1]));
      const tmp = document.createElement("div");
      tmp.innerHTML = html;
      tmp.querySelectorAll("[data-good-id]").forEach(el => s.add(String(el.getAttribute("data-good-id"))));
      ids = Array.from(s).slice(0, 60);
    }

    if (!ids.length) return false;

    // 3) 直接切到商品模式：用 ids 查詢並渲染
    const resp = await fetch("/api/search", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ ids })
    });
    const data = await resp.json();
    if (data && Array.isArray(data.items)) {
      renderList(data.items);
      if (window.applyPromoLine) window.applyPromoLine();
    }
    return true;
  }

  return { onUserSend };
}

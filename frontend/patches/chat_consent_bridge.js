export function installChatConsentBridge(getLastAssistantHtml, renderList) {
  const agreeLex = /^(要|OK|Ok|ok|好|可以|行|確定|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;
  async function onUserSend(text) {
    if (!agreeLex.test((text || "").trim())) return false;
    const html = (typeof getLastAssistantHtml === "function") ? getLastAssistantHtml() : "";
    const ids = new Set();
    const hashIds = [...(html.matchAll(/#(\d{6,})/g))].map(m => m[1]);
    hashIds.forEach(id => ids.add(String(id)));
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    tmp.querySelectorAll("[data-good-id]").forEach(el => ids.add(String(el.getAttribute("data-good-id"))));
    if (ids.size === 0) return false;
    const resp = await fetch("/api/search", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ ids: Array.from(ids).slice(0, 60) })
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

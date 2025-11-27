// goods_action 雙保險橋接器
export function installChatConsentBridge(getLastAssistantJson, getLastAssistantHtml, renderList) {
  const agreeLex = /^(要|OK|Ok|ok|好|可以|行|確定|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;

  async function onUserSend(text) {
    if (!agreeLex.test((text || "").trim())) return false;

    // 1️⃣ 取最後一次 AI JSON
    let ids = [];
    try {
      const j = (typeof getLastAssistantJson === "function") ? getLastAssistantJson() : null;
      if (j?.suggestion_ids?.length) ids = j.suggestion_ids.slice(0, 60);
      else if (j?.action?.items?.length) ids = j.action.items.map(it => it.id).slice(0, 60);
    } catch (e) {}

    // 2️⃣ 退路：HTML 解析
    if (!ids.length) {
      const html = (typeof getLastAssistantHtml === "function") ? getLastAssistantHtml() : "";
      const set = new Set();
      for (const m of html.matchAll(/#(\d{6,})/g)) set.add(m[1]);
      const tmp = document.createElement("div");
      tmp.innerHTML = html;
      tmp.querySelectorAll("[data-good-id]").forEach(el => set.add(el.dataset.goodId));
      ids = [...set].slice(0, 60);
    }

    if (!ids.length) return false;

    // 3️⃣ 呼叫 /api/search 顯示商品
    const resp = await fetch("/api/search", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ ids })
    });
    const data = await resp.json();
    if (data?.items?.length) {
      renderList(data.items);
      if (window.applyPromoLine) window.applyPromoLine();
    }
    return true;
  }

  return { onUserSend };
}

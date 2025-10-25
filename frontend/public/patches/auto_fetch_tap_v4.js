// frontend/public/patches/auto_fetch_tap_v4.js (v4: UI+fetch 雙層攔截)
(() => {
  if (window.__agreePatchInstalledV4) return;
  window.__agreePatchInstalledV4 = true;
  console.log("[auto_fetch_tap_v4] installed ✅");

  const agreeLex = /^(要|OK|Ok|ok|好|可以|行|確定|需要|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;

  // 抓取商品ID（從最近一次AI回覆）
  const grabIds = () => {
    const j = window.lastAssistantJson || {};
    let ids = [];
    if (j.suggestion_ids?.length) ids = j.suggestion_ids.slice(0, 60);
    else if (j.action?.items?.length) ids = j.action.items.map(it => it.id).slice(0, 60);
    return ids;
  };

  // === Fetch層：自動保存 /api/chat 回應內容 ===
  const origFetch = window.fetch.bind(window);
  window.fetch = async function(input, init = {}) {
    const url = typeof input === "string" ? input : (input?.url || "");
    const method = (init?.method || "GET").toUpperCase();
    const res = await origFetch(input, init);
    if (url.includes("/api/chat") && method === "POST") {
      res.clone().json().then(j => window.lastAssistantJson = j).catch(()=>{});
    }
    return res;
  };

  // === UI層攔截：submit 捕獲 + Enter捕獲 ===
  const triggerSearch = () => {
    const ids = grabIds();
    if (!ids.length) return;
    console.log("[auto_fetch_tap_v4] trigger search:", ids);
    fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids })
    })
      .then(r => r.json())
      .then(data => {
        if (!data?.items?.length) return;
        if (typeof window.renderList === "function") window.renderList(data.items);
        else document.dispatchEvent(new CustomEvent("goods:render-list", { detail: data.items }));
        if (window.applyPromoLine) window.applyPromoLine();
      })
      .catch(e => console.warn("[auto_fetch_tap_v4] fetch /api/search error:", e));
  };

  // 攔 submit
  document.addEventListener("submit", e => {
    const input = e.target.querySelector("textarea, input[type=text], input[type=search]");
    const text = (input?.value || "").trim();
    if (!agreeLex.test(text)) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if (input) input.value = "";
    console.log("[auto_fetch_tap_v4] intercepted submit:", text);
    triggerSearch();
  }, true);

  // 攔 Enter（防 form-less 聊天框）
  document.addEventListener("keydown", e => {
    const el = e.target;
    if (e.key !== "Enter") return;
    if (!(el.tagName === "TEXTAREA" || el.type === "text" || el.type === "search")) return;
    const text = el.value.trim();
    if (!agreeLex.test(text)) return;
    e.preventDefault(); e.stopImmediatePropagation();
    el.value = "";
    console.log("[auto_fetch_tap_v4] intercepted keydown:", text);
    triggerSearch();
  }, true);
})();

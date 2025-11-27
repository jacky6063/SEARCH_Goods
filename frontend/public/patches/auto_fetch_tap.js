// frontend/public/patches/auto_fetch_tap.js (UI層修正版)
(() => {
  if (window.__agreePatchInstalled) return;
  window.__agreePatchInstalled = true;
  console.log("[auto_fetch_tap_v3] installed");

  const agreeLex = /^(要|OK|Ok|ok|好|可以|行|確定|需要|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;

  const grabIds = () => {
    const j = window.lastAssistantJson || {};
    let ids = [];
    if (j.suggestion_ids?.length) ids = j.suggestion_ids.slice(0, 60);
    else if (j.action?.items?.length) ids = j.action.items.map(it => it.id).slice(0, 60);
    return ids;
  };

  // 🔸 攔截使用者送出聊天輸入（UI 層）
  document.addEventListener("submit", e => {
    const input = e.target.querySelector("textarea, input[type=text], input[type=search]");
    const text = (input?.value || "").trim();
    if (!agreeLex.test(text)) return;

    e.preventDefault();
    e.stopImmediatePropagation();
    if (input) input.value = "";
    console.log("[auto_fetch_tap_v3] intercepted:", text);

    const ids = grabIds();
    if (!ids.length) return;

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
      .catch(err => console.warn("[auto_fetch_tap_v3] fetch error:", err));
  }, true);
})();

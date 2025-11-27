// frontend/public/patches/original_suggestion_all.js
// 功能：
//  1) 從最後一次 AI JSON/HTML 盡可能收集「全部建議商品」的 ids（含多分組/類別 → 扁平化）
//  2) 監聽「1.原建議」點擊與同意詞（要/OK/需要…），直接切商品模式
//  3) 保持與既有 renderList / applyPromoLine 相容

(() => {
  if (window.__origSuggestAllInstalled) return;
  window.__origSuggestAllInstalled = true;
  console.log("[orig_suggest_all] installed");

  // —— 允許觸發的同意詞 —— //
  const agreeLex = /^(1|要|OK|Ok|ok|好|可以|行|確定|需要|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;

  const ID_PATTERN = /^[A-Za-z0-9-]{4,}$/;

  // —— 扁平化收集全部 IDs —— //
  function collectAllIdsFromJson(j) {
    const set = new Set();

    const put = (v) => {
      if (!v) return;
      if (typeof v === 'string' || typeof v === 'number') {
        const s = String(v).trim();
        // 商品編號可能為條碼(純數字)或字母+數字（如 VS030078-8035）
        if (ID_PATTERN.test(s) && /[0-9]/.test(s)) set.add(s);
      }
    };

    const scanObj = (o) => {
      if (!o || typeof o !== 'object') return;
      // 常見鍵名
      put(o.GoodIden || o.goodId || o.id || o.sku || o.barcode);
      // 避免掃到超大內容
      for (const k of Object.keys(o)) {
        const v = o[k];
        if (Array.isArray(v)) scanArr(v);
        else if (v && typeof v === 'object') scanObj(v);
      }
    };

    const scanArr = (arr) => {
      for (const it of arr) {
        if (Array.isArray(it)) scanArr(it);
        else if (it && typeof it === 'object') scanObj(it);
        else put(it);
      }
    };

    try {
      if (j?.suggestion_ids) scanArr(j.suggestion_ids);
      // 新版：structured_products / structured_payload.items
      if (j?.structured_products) scanArr(j.structured_products);
      if (j?.structured_payload?.items) scanArr(j.structured_payload.items);
      // 常見結構變體：category_suggestions、groups、categories、items、recommendations
      if (j?.category_suggestions) scanObj(j.category_suggestions);
      if (j?.groups) scanArr(j.groups);
      if (j?.categories) scanArr(j.categories);
      if (j?.items) scanArr(j.items);
      if (j?.recommendations) scanArr(j.recommendations);
      if (j?.data) scanObj(j.data);
    } catch (e) {
      console.warn("[orig_suggest_all] JSON scan error:", e);
    }
    return Array.from(set);
  }

  function collectAllIdsFromHtml(html) {
    const set = new Set();
    if (!html) return [];
    try {
      for (const m of html.matchAll(/#([A-Za-z0-9-]{4,})/g)) set.add(m[1]);
      const tmp = document.createElement("div");
      tmp.innerHTML = html;
      tmp.querySelectorAll("[data-good-id]").forEach(el => set.add(String(el.getAttribute("data-good-id"))));
      const text = tmp.textContent || "";
      for (const m of text.matchAll(/商品編號[：:]\s*([A-Za-z0-9-]{4,})/g)) {
        set.add(m[1]);
      }
      // 也處理「價格: 49元」這種文字不會影響；只抓 data-good-id / #471...
    } catch (e) {
      console.warn("[orig_suggest_all] HTML scan error:", e);
    }
    return Array.from(set);
  }

  function getAllIds() {
    const j = window.lastAssistantJson || null;
    let ids = collectAllIdsFromJson(j);
    if (!ids.length) {
      const msg = document.querySelector('.bubble.assistant:last-of-type, .assistant-message:last-of-type, .msg-assistant:last-of-type');
      ids = collectAllIdsFromHtml(msg ? msg.innerHTML : '');
    }
    // 限制最多帶 60 筆以免過重
    return ids.slice(0, 60);
  }

  async function goSearchByIds(ids) {
    if (!ids || !ids.length) return false;
    const resp = await fetch("/api/search", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ ids })
    });
    const data = await resp.json().catch(()=>null);
    if (!data || !Array.isArray(data.items) || !data.items.length) return false;

    if (typeof window.renderList === "function") window.renderList(data.items);
    else document.dispatchEvent(new CustomEvent("goods:render-list", { detail: data.items }));

    if (window.applyPromoLine) window.applyPromoLine();
    return true;
  }

  function handleConsent(text) {
    const t = (text || "").trim();
    if (!agreeLex.test(t)) return false;
    const ids = getAllIds();
    if (!ids.length) {
      console.warn("[orig_suggest_all] no ids collected");
      return false;
    }
    console.log("[orig_suggest_all] consent → switch_to_search, ids:", ids);
    goSearchByIds(ids);
    return true;
  }

  // —— 1) 監聽 submit（捕獲） —— //
  document.addEventListener("submit", (ev) => {
    try {
      const input = ev.target.querySelector("textarea, input[type=text], input[type=search]");
      const val = input ? input.value : '';
      if (handleConsent(val)) {
        ev.stopImmediatePropagation();
        ev.preventDefault();
        if (input) input.value = '';
      }
    } catch(e) {}
  }, true);

  // —— 2) 監聽 Enter（捕獲，for 非 form 輸入） —— //
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Enter") return;
    try {
      const a = document.activeElement;
      if (!a || !/^(INPUT|TEXTAREA)$/.test(a.tagName)) return;
      const val = a.value || '';
      if (handleConsent(val)) {
        ev.stopImmediatePropagation();
        ev.preventDefault();
        a.value = '';
      }
    } catch(e) {}
  }, true);

  // —— 3) 監聽「1.原建議」點擊 —— //
  const clickMatch = (el) => {
    const txt = (el?.textContent || "").trim();
    return /^1[\.、．]?\s*原建議$/.test(txt) || /^原建議$/.test(txt) || /^1$/.test(txt);
  };
  document.addEventListener("click", (ev) => {
    try {
      let el = ev.target;
      for (let i = 0; el && i < 3; i++) { // 往上找 2 層，容錯
        if (clickMatch(el)) {
          const ids = getAllIds();
          if (ids.length) {
            console.log("[orig_suggest_all] click 1.原建議 → switch_to_search");
            goSearchByIds(ids);
            ev.stopPropagation();
            ev.preventDefault();
          }
          break;
        }
        el = el.parentElement;
      }
    } catch(e) {}
  }, true);
})();

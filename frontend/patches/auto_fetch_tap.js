(() => {
  if (window.__autoFetchTapInstalledV2) return; window.__autoFetchTapInstalledV2 = true;

  const agreeLex = /^(要|OK|Ok|ok|好|可以|行|確定|需要|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;

  // 從上一則助理資料 or HTML 取商品 ID
  function grabIds() {
    const j = window.lastAssistantJson || null;
    let ids = [];
    if (j?.suggestion_ids?.length) ids = j.suggestion_ids.slice(0, 60);
    else if (j?.action?.items?.length) ids = j.action.items.map(it => it.id).slice(0, 60);

    if (!ids.length) {
      const msg = document.querySelector('.assistant-message:last-of-type');
      const html = msg ? msg.innerHTML : '';
      const s = new Set();
      if (html) {
        for (const m of html.matchAll(/#(\d{6,})/g)) s.add(m[1]);
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        tmp.querySelectorAll('[data-good-id]').forEach(el => s.add(String(el.getAttribute('data-good-id'))));
      }
      ids = Array.from(s).slice(0,60);
    }
    return ids;
  }

  const origFetch = window.fetch.bind(window);

  window.fetch = async function(input, init={}) {
    const url = typeof input === 'string' ? input : (input?.url || '');
    const method = (init?.method || 'GET').toUpperCase();

    // 只攔 /api/chat 的 POST
    if (url.includes('/api/chat') && method === 'POST') {
      try {
        // 解析 body 取得 text
        let bodyText = '';
        if (init?.body && typeof init.body === 'string') {
          bodyText = init.body;
        } else if (init?.body instanceof Blob) {
          bodyText = await init.body.text();
        }
        let text = '';
        try { text = JSON.parse(bodyText)?.text || ''; } catch(e) { text = ''; }

        // 命中同意詞 → 直接短路：不發請求，回 action 給前端
        if (agreeLex.test((text||'').trim())) {
          const ids = grabIds();
          if (ids.length) {
            const fake = {
              ok: true,
              reply: "", // 不要任何話術
              suggestion_ids: ids,
              action: { type: "switch_to_search", items: ids.map(id => ({ id })) },
              meta: { intercepted: true, reason: "agree" }
            };
            const blob = new Blob([JSON.stringify(fake)], { type: "application/json" });
            const res = new Response(blob, { status: 200, headers: { "Content-Type": "application/json" } });
            console.debug("[auto_fetch_tap] intercepted agree, switching to search:", ids);
            // 同時主動發起商品查詢（雙保險，若前端沒吃 action 也能渲染）
            try {
              const r = await origFetch("/api/search", {
                method: "POST",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({ ids })
              });
              const data = await r.json();
              if (data?.items?.length) {
                if (typeof window.renderList === "function") window.renderList(data.items);
                else document.dispatchEvent(new CustomEvent("goods:render-list", { detail: data.items }));
                if (window.applyPromoLine) window.applyPromoLine();
              }
            } catch(e) { /* ignore */ }
            return res; // ★ 直接回假回應；不會再顯示「好的…」氣泡
          }
        }
      } catch (e) {
        console.warn("[auto_fetch_tap] intercept error:", e);
      }
    }

    // 一般流程：放行，並把 /api/chat 的回應 JSON 存起來
    const res = await origFetch(input, init);
    try {
      const clone = res.clone();
      if (url.includes('/api/chat') && method === 'POST') {
        clone.json().then(j => { window.lastAssistantJson = j; }).catch(()=>{});
      }
    } catch(e) {}
    return res;
  };
})();

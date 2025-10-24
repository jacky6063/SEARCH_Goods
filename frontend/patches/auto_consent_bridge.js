(() => {
  if (window.__autoConsentBridgeInstalled) return; window.__autoConsentBridgeInstalled = true;
  const agreeLex = /^(要|OK|Ok|ok|好|可以|行|確定|需要|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;

  async function goSearchByIds(ids) {
    if (!ids || !ids.length) return false;
    const resp = await fetch('/api/search', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ ids })
    });
    const data = await resp.json().catch(()=>null);
    if (!data || !Array.isArray(data.items)) return false;

    if (typeof window.renderList === 'function') {
      window.renderList(data.items);
    } else {
      document.dispatchEvent(new CustomEvent('goods:render-list', { detail: data.items }));
    }
    if (window.applyPromoLine) window.applyPromoLine();
    return true;
  }

  function grabIdsFromLastAssistant() {
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

  function interceptText(textRaw) {
    const text = (textRaw||'').trim();
    if (!agreeLex.test(text)) return false;
    const ids = grabIdsFromLastAssistant();
    if (!ids.length) return false;
    goSearchByIds(ids);
    document.dispatchEvent(new CustomEvent('goods:consent-intercepted', { detail: { text, ids } }));
    return true;
  }

  window.addEventListener('submit', (ev) => {
    try {
      const form = ev.target;
      const input = form.querySelector('textarea, input[type="text"], input[type="search"]');
      const val = input ? input.value : '';
      if (interceptText(val)) {
        ev.stopImmediatePropagation(); ev.preventDefault();
        if (input) input.value = '';
      }
    } catch(e) {}
  }, true);

  window.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter') return;
    try {
      const a = document.activeElement;
      if (!a || !/^(INPUT|TEXTAREA)$/.test(a.tagName)) return;
      const val = a.value || '';
      if (interceptText(val)) {
        ev.stopImmediatePropagation(); ev.preventDefault();
        a.value = '';
      }
    } catch(e) {}
  }, true);
})();

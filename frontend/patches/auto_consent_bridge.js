(() => {
  if (window.__autoConsentBridgeInstalled) return; window.__autoConsentBridgeInstalled = true;

  const agreeLex = /^(要|OK|Ok|ok|好|可以|行|確定|需要|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;

  async function goSearchByIds(ids) {
    if (!ids || !ids.length) return false;
    const resp = await fetch('/api/search', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ ids })
    });
    const data = await resp.json().catch(()=>null);
    if (!data || !Array.isArray(data.items)) return false;
    // 嘗試呼叫全域渲染器；若沒有，觸發自訂事件給你的 App 接手
    if (typeof window.renderList === 'function') {
      window.renderList(data.items);
    } else {
      document.dispatchEvent(new CustomEvent('goods:render-list', { detail: data.items }));
    }
    // 宣傳短文
    if (window.applyPromoLine) window.applyPromoLine();
    return true;
  }

  function grabIdsFromLastAssistant() {
    // 1) 最可靠：上一則 AI JSON 的 suggestion_ids 或 action.items
    const j = window.lastAssistantJson || null;
    let ids = [];
    if (j?.suggestion_ids?.length) ids = j.suggestion_ids.slice(0, 60);
    else if (j?.action?.items?.length) ids = j.action.items.map(it => it.id).slice(0, 60);

    // 2) 退路：從最後一則助理訊息 HTML 解析 #471... 或 data-good-id
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
    // 直接進商品模式
    goSearchByIds(ids);
    // 廣播（給應用程式知道已攔截）
    document.dispatchEvent(new CustomEvent('goods:consent-intercepted', { detail: { text, ids } }));
    return true;
  }

  // A) 監聽任何 form 提交（捕獲階段），攔截同意詞
  window.addEventListener('submit', (ev) => {
    try {
      const form = ev.target;
      const input = form.querySelector('textarea, input[type="text"], input[type="search"]');
      const val = input ? input.value : '';
      if (interceptText(val)) {
        ev.stopImmediatePropagation();
        ev.preventDefault();
        if (input) input.value = ''; // 清空輸入框
      }
    } catch(e) {}
  }, true);

  // B) 監聽 Enter keydown（避免某些實作不是 form submit）
  window.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter') return;
    try {
      const active = document.activeElement;
      if (!active) return;
      if (!/^(INPUT|TEXTAREA)$/.test(active.tagName)) return;
      const val = active.value || '';
      if (interceptText(val)) {
        ev.stopImmediatePropagation();
        ev.preventDefault();
        active.value = '';
      }
    } catch(e) {}
  }, true);

})();

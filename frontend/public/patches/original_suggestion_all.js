// frontend/public/patches/original_suggestion_all.js (v3)
(() => {
  if (window.__origSuggestAllInstalledV3) return;
  window.__origSuggestAllInstalledV3 = true;
  console.log("[orig_suggest_all] v3 installed");

  const agreeLex = /^(1|要|OK|Ok|ok|好|可以|行|確定|需要|沒問題|那就這些|都可以|ＯＫ|Ｏk|ｏｋ)\s*$/;

  // ====== 備援：攔截 XHR，抓 /api/chat 回應 ======
  (function patchXHR(){
    if (window.__xhrPatched) return;
    window.__xhrPatched = true;
    const open = XMLHttpRequest.prototype.open;
    const send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url, async, user, pass){
      this.__url = url;
      this.__method = (method||'GET').toUpperCase();
      return open.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function(body){
      this.addEventListener('load', () => {
        try{
          if ((this.__url||'').includes('/api/chat') && this.__method === 'POST') {
            const ct = this.getResponseHeader('content-type') || '';
            if (ct.includes('application/json')) {
              const j = JSON.parse(this.responseText);
              window.lastAssistantJson = j;
            }
          }
        }catch(e){}
      });
      return send.apply(this, arguments);
    };
  })();

  // ====== 從 JSON 結構蒐集 ======
  function collectFromJson(j){
    const set = new Set();
    const put = v => {
      if (!v) return;
      const s = String(v).trim();
      if (/^\d{6,}$/.test(s)) set.add(s);
    };
    const walk = o => {
      if (!o || typeof o!=='object') return;
      // 常見鍵
      put(o.GoodIden || o.goodId || o.id || o.sku || o.barcode);
      for (const k in o){
        const v=o[k];
        if (Array.isArray(v)) v.forEach(walk);
        else if (v && typeof v === 'object') walk(v);
        else put(v);
      }
    };
    try{
      if (j) walk(j);
    }catch(e){}
    return [...set];
  }

  // ====== 從「隱藏 JSON」純文字解析 ======
  function collectFromHiddenText(text){
    const set = new Set();
    if (!text) return [];
    try{
      // 把可能跟在「隱藏 JSON」後的 JSON 片段抓出來
      const m = text.match(/(?:隱藏(?:的)?\s*JSON(?:\s*格式)?\s*[:：]\s*)([\s\S]+)$/i);
      if (m && m[1]){
        const raw = m[1].trim();
        // 嘗試找到第一個大括號或方括號作為 JSON 起點
        const idx = raw.search(/[\[\{]/);
        if (idx >= 0){
          const jsonStr = raw.slice(idx);
          // 盡力解析（必要時裁掉奇怪尾巴）
          let parsed=null;
          try{ parsed = JSON.parse(jsonStr); }
          catch(e){
            // 容錯：找到最後一個]或}作為終點
            const end = Math.max(jsonStr.lastIndexOf(']'), jsonStr.lastIndexOf('}'));
            if (end>0){
              try{ parsed=JSON.parse(jsonStr.slice(0,end+1)); }catch(_){}
            }
          }
          if (parsed){
            collectFromJson(parsed).forEach(id=>set.add(id));
          }else{
            // 後備：直接抓 6 碼以上純數字
            for (const m2 of jsonStr.matchAll(/\d{6,}/g)) set.add(m2[0]);
          }
        }else{
          for (const m2 of raw.matchAll(/\d{6,}/g)) set.add(m2[0]);
        }
      }
    }catch(e){}
    return [...set];
  }

  function getAssistantLastText(){
    const msg = document.querySelector('.assistant-message:last-of-type, .msg-assistant:last-of-type, .chat-ai:last-of-type, .bot:last-of-type');
    return msg ? msg.textContent || '' : '';
  }

  function getAllIds(){
    // 1) 先從 lastAssistantJson（fetch/XHR 擷取）收集
    let ids = collectFromJson(window.lastAssistantJson);
    if (ids.length) return dedupe(ids);

    // 2) 再嘗試從「隱藏 JSON」純文字收集
    const txt = getAssistantLastText();
    ids = collectFromHiddenText(txt);
    if (ids.length) return dedupe(ids);

    // 3) 最後從頁面文字撈 6 碼+數字（保底）
    const set = new Set();
    for (const m of (txt||'').matchAll(/\d{6,}/g)) set.add(m[0]);
    return dedupe([...set]);
  }

  const dedupe = arr => [...new Set(arr)].slice(0, 80);

  async function goSearchByIds(ids){
    if (!ids.length) return false;
    const res = await fetch('/api/search', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ ids })
    });
    const data = await res.json().catch(()=>null);
    if (!data?.items?.length) return false;
    if (typeof window.renderList === 'function') window.renderList(data.items);
    else document.dispatchEvent(new CustomEvent('goods:render-list', { detail: data.items }));
    if (window.applyPromoLine) window.applyPromoLine();
    return true;
  }

  function handleConsent(text){
    const t=(text||'').trim();
    if (!agreeLex.test(t)) return false;
    const ids=getAllIds();
    if (!ids.length){ console.warn('[orig_suggest_all] no ids'); return false; }
    console.log('[orig_suggest_all] consent → ids:', ids);
    goSearchByIds(ids);
    return true;
  }

  // submit 捕獲
  document.addEventListener('submit', ev=>{
    try{
      const input = ev.target.querySelector('textarea, input[type=text], input[type=search]');
      const val = input ? input.value : '';
      if (handleConsent(val)){ ev.preventDefault(); ev.stopImmediatePropagation(); if (input) input.value=''; }
    }catch(e){}
  }, true);

  // Enter 捕獲
  document.addEventListener('keydown', ev=>{
    if (ev.key!=='Enter') return;
    const el = ev.target;
    if (!(el && (/^(INPUT|TEXTAREA)$/).test(el.tagName))) return;
    const val = el.value||'';
    if (handleConsent(val)){ ev.preventDefault(); ev.stopImmediatePropagation(); el.value=''; }
  }, true);

  // 點擊「1.原建議」按鈕/文字（更寬鬆）
  const isOriginalBtn = (el) => {
    const t=(el?.textContent||'').replace(/\s+/g,'').trim();
    return /^1[\.、．]?原建議$/.test(t) || /^原建議商品?卡片?$/.test(t) || /^原建議$/.test(t) || t==='1';
  };
  document.addEventListener('click', ev=>{
    let el=ev.target, hop=0;
    while (el && hop<4){
      if (isOriginalBtn(el)){
        const ids=getAllIds();
        if (ids.length){ goSearchByIds(ids); ev.preventDefault(); ev.stopPropagation(); }
        break;
      }
      el=el.parentElement; hop++;
    }
  }, true);
})();

// frontend/public/patches/suppress_hidden_json.js
(() => {
  if (window.__suppressHiddenJsonInstalled) return;
  window.__suppressHiddenJsonInstalled = true;
  console.log("[suppress_hidden_json] installed");

  const re = /（\s*隱藏\s*JSON\s*：[\s\S]*?）/g; // 全形括號＋內容
  function stripHiddenJsonIn(el) {
    if (!el) return;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(n => {
      const t = n.nodeValue || '';
      if (re.test(t)) n.nodeValue = t.replace(re, '');
    });
  }

  // 初始化清理
  stripHiddenJsonIn(document.body);

  // 動態新增時清理
  const mo = new MutationObserver(muts => {
    muts.forEach(m => {
      m.addedNodes && m.addedNodes.forEach(n => {
        if (n.nodeType === 1) stripHiddenJsonIn(n);
      });
      if (m.type === 'characterData' && m.target?.nodeType === 3) {
        const t = m.target.nodeValue || '';
        if (re.test(t)) m.target.nodeValue = t.replace(re, '');
      }
    });
  });
  mo.observe(document.body, { childList: true, subtree: true, characterData: true });
})();

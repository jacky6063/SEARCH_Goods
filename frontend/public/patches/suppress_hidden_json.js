// frontend/public/patches/suppress_hidden_json.js (v2)
(() => {
  if (window.__suppressHiddenJsonInstalledV2) return;
  window.__suppressHiddenJsonInstalledV2 = true;
  console.log("[suppress_hidden_json] v2 installed");

  // 支援多種寫法：
  // 「（隱藏 JSON：...）」、"隱藏的 JSON 格式："、"隱藏JSON:"
  const PATTERNS = [
    /（\s*隱藏\s*JSON\s*：[\s\S]*?）/g,                    // 全形括號版本
    /(?:以下是)?\s*隱藏(?:的)?\s*JSON(?:\s*格式)?\s*[:：]\s*[\s\S]*$/gi // 行尾型
  ];

  const strip = (root = document) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const n of nodes) {
      let t = n.nodeValue || '';
      let changed = false;
      for (const re of PATTERNS) {
        if (re.test(t)) {
          t = t.replace(re, '');
          changed = true;
        }
      }
      if (changed) n.nodeValue = t;
    }
  };

  strip();
  new MutationObserver(muts => {
    for (const m of muts) {
      if (m.addedNodes) {
        m.addedNodes.forEach(n => n.nodeType === 1 && strip(n));
      }
      if (m.type === 'characterData' && m.target?.nodeType === 3) {
        let t = m.target.nodeValue || '';
        for (const re of PATTERNS) t = t.replace(re, '');
        m.target.nodeValue = t;
      }
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true});
})();

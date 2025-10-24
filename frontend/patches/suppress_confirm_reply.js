(() => {
  if (window.__suppressConfirmReplyInstalled) return; window.__suppressConfirmReplyInstalled = true;
  const patterns = [
    /^好的，為您顯示這些商品。?$/i,
    /^已為您顯示商品。?$/i,
    /^即將顯示推薦商品。?$/i
  ];
  const isConfirmText = (t) => patterns.some(re => re.test((t||'').trim()));
  function sweep(root=document) {
    const nodes = root.querySelectorAll('.assistant-message, .msg-assistant, .chat-ai, .bot, p, div');
    nodes.forEach(n => {
      const txt = (n.textContent||'').trim();
      if (txt && isConfirmText(txt)) n.remove();
    });
  }
  sweep();
  const mo = new MutationObserver(muts => muts.forEach(m => m.addedNodes && m.addedNodes.forEach(n => n.nodeType===1 && sweep(n))));
  mo.observe(document.body, {childList:true, subtree:true});
})();

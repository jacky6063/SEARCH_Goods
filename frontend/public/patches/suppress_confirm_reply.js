// frontend/public/patches/suppress_confirm_reply.js
(() => {
  if (window.__suppressConfirmReplyInstalled) return;
  window.__suppressConfirmReplyInstalled = true;
  console.log("[suppress_confirm_reply] installed");

  const patterns = [
    /^好的，為您顯示這些商品。?$/i,
    /^已為您顯示商品。?$/i,
    /^即將顯示推薦商品。?$/i
  ];
  const isHit = t => patterns.some(re => re.test((t || '').trim()));

  function sweep(root = document) {
    root.querySelectorAll('.assistant-message, .msg-assistant, .chat-ai, .bot, p, div')
      .forEach(el => {
        const txt = (el.textContent || '').trim();
        if (txt && isHit(txt)) el.remove();
      });
  }

  sweep();
  new MutationObserver(muts =>
    muts.forEach(m => m.addedNodes &&
      m.addedNodes.forEach(n => n.nodeType === 1 && sweep(n))))
    .observe(document.body, { childList: true, subtree: true });
})();

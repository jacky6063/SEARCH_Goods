// frontend/public/patches/auto_boot.js
(async () => {
  console.log("[auto_boot] loading patches...");
  try { await import('./auto_fetch_tap.js'); } catch(e){ console.error(e); }
  try { await import('./suppress_confirm_reply.js'); } catch(e){}
  console.log("[auto_boot] patches initialized ✅");
})();

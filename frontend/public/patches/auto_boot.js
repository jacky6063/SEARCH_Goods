// frontend/public/patches/auto_boot.js (v4)
(async () => {
  console.log("[auto_boot] loading patches...");
  try { await import('./original_suggestion_all.js'); } catch(e){ console.error(e); }
  try { await import('./suppress_hidden_json.js'); } catch(e){ console.error(e); }
  try { await import('./auto_fetch_tap_v4.js'); } catch(e){ console.error(e); }
  try { await import('./suppress_confirm_reply.js'); } catch(e){}
  console.log("[auto_boot] patches initialized ✅");
})();

(async () => {
  try { await import('/patches/auto_fetch_tap.js'); } catch(e) {}
  try { await import('/patches/auto_consent_bridge.js'); } catch(e) {}
  try { await import('/patches/suppress_confirm_reply.js'); } catch(e) {}
})();

(async () => {
  try { await import('/patches/auto_fetch_tap.js'); } catch(e) {}
  try { await import('/patches/auto_consent_bridge.js'); } catch(e) {}
  try { await import('/patches/suppress_confirm_reply.js'); } catch(e) {}
  // 若頁面有自訂事件，可在此再做必要掛鉤
})();

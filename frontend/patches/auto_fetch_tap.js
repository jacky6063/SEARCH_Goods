(() => {
  if (window.__autoFetchTapInstalled) return; window.__autoFetchTapInstalled = true;
  const origFetch = window.fetch;
  window.fetch = async function(input, init) {
    const res = await origFetch(input, init);
    try {
      const url = typeof input === 'string' ? input : (input?.url || '');
      const method = (init?.method || 'GET').toUpperCase();
      const clone = res.clone();
      if (url.includes('/api/chat') && method === 'POST') {
        clone.json().then(j => { window.lastAssistantJson = j; }).catch(()=>{});
      }
    } catch(e) {}
    return res;
  };
})();

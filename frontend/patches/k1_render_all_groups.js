
// --- Hotfix helper for Card 1: render all groups ---
export async function handleSwitchToSearchAllItems(action) {
  const ids = (action.items || []).map(x => x.id).filter(Boolean);
  if (!ids.length) return;

  const resp = await fetch('/api/search', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ ids })
  });
  const data = await resp.json();

  if (data && data.items && Array.isArray(data.items)) {
    if (typeof renderList === 'function') {
      renderList(data.items);
    } else {
      console.log('Search results:', data.items);
    }
  }
}

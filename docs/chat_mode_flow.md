# Chat Mode Flow Audit (2025-10-23)

## 1. Backend `/api/chat`

### Request contract
- **Endpoint**: `POST /api/chat`
- **Payload (`ChatReq`)**
  - `message`: user free-form text.
  - `history`: array of prior turns (kept at most 40 entries server-side).
  - `topn`: number of products to surface (default 8).
  - `session_id`: string (used to scope alignment caches).

### High-level execution path
1. **Shortcut commands**: literal `"1" | "2" | "3"` trigger suggestion shortcuts.
2. **Affirmation handling**: phrases in `AFFIRM_WHITELIST` reuse cached alignment items fetched previously.
3. **LLM plan mode**:
   - Builds catalog snapshot via `get_catalog_snapshot(limit=600)`.
   - Calls `llm_generate_plan` to attempt multi-item plan creation.
   - `plan_result["plan"]["items"]` validated against CSV by id or fuzzy name.
   - Successful validations populate chat `items` payload with enriched descriptions (qty, subtotal, note).
   - `meta`: budget info (`subtotal`, `budget`, `remain`).
   - Alignment caches updated via `_store_alignment`, including `SESSION_ALIGN_CACHE` and `SUGGEST_CACHE` (ids, rows, derived query terms).
4. **Fallback to conversational LLM (`chat_reply`)**:
   - `result` may include `reply`, `alignment`, `auto_suggest`, `query_terms`, `action`.
   - Replies may embed JSON snippet `{"intent":"product_align", ...}`; regex `ALIGN_JSON_RE` extracts & sanitizes.
   - `_store_alignment` sanitizes item list fetched via `get_items_by_ids`, stores up to 8 ids/names.
   - Auto-suggest prepared when alignment available: chooses type via `classify_recommendation_type`, fetches suggestion rows, returns `auto_suggest` payload.

### Response contract (`ChatResp`)
- `reply`: assistant text (string).
- `action`: e.g. `{ "type": "switch_to_search", "items": [{id,name}, ...], "reason": str }` or `{ "type": "none" }`.
- `alignment`: sanitized structure `{ intent: "product_align", items: [{id,name}], need_confirm_show_details: bool, reason }`.
- `auto_suggest`: when available, `{ type: int, label: str, items: formatted_cards[], ids: [str] }`.
- `items`: populated only by plan workflow (formatted via `format_for_chat`).
- `meta`: currently used for plan totals.

### Session caches
- `SESSION_ALIGN_CACHE[session_id]`
  - `ids`: latest aligned id list (<=8)
  - `items`: sanitized label list
  - `ts`: timestamp
- `SUGGEST_CACHE[session_id]`
  - `align_ids` / `align_rows`
  - `query_terms`: token extraction from user message
  - `ts`
- `SESSION_CACHE_TTL`: default 600 seconds via env `CHAT_ALIGNMENT_CACHE_TTL`.
- `_cleanup_session_cache` prunes expired entries each request.

### Suggestion helpers
- `_build_suggestion` dispatches:
  1. `suggest_original_ids` – replay aligned ids.
  2. `suggest_on_sale_related` – filters by `SpecialOffer` and query terms.
  3. `suggest_complementary` – heuristics on categories.
- `/api/suggest` reuses caches to fetch formatted cards via `format_for_chat`.

## 2. Frontend `frontend/index.html`

### Mode management
- `chat-mode` vs `search-mode` toggled via `setMode`.
- Default launch = chat mode with welcome bubble.
- `switchToSearch(queryText, itemIds, prefetchedItems)`
  - Accepts query string, optional id list, optional preformatted items.
  - When `prefetchedItems` present (e.g. from chat auto-suggest cache), bypasses API call and renders cards immediately. Pagination disabled.
  - Otherwise, if `itemIds` exists ⇒ POST `/api/search` with `{ ids }` (calls backend reorder logic).
  - Else fallback to query search with pagination (page size 30).

### Chat flow integration
- `sendChat()`
  - Sends message + last 10 history entries to `/api/chat` (`chatEndpoint = buildBackendUrl('chat')`).
  - Renders user & assistant bubbles.
  - Appends turn to local `chatHistory` (capped at 40).
  - Handles `auto_suggest` response: caches by type (`latestSuggestCache[type] = { ids, items, meta }`), shows prompt bubble.
  - Handles `items` array (plan result) similarly cached under type `1` and annotated by `meta`.

### Suggestion triggers
- Inputting `1/2/3` or clicking quick buttons calls `handleSuggestTrigger(type)`.
  - If cached, immediate `switchToSearch` with cached items.
  - Otherwise requests `/api/suggest` to refresh.

### Alignment → search hand-off today
- When backend responds with `action.type === 'switch_to_search'`, frontend expects sanitized list (`{id,name}`). Currently the UI does not auto-trigger search; user must click button or input command. `switchToSearch` handles both ids and prefetched cards.
- No existing UI for grouped results; cards rendered flat per `format_for_chat` output.

### Chat → search state tracking
- `latestSuggestCache` persists across session for each suggestion type.
- `switchToSearch` updates `resultCount`, resets pagination metadata, and notes status message.
- `backToChat` button toggles mode.

## 3. Identified integration points for new requirements

1. **Backend** needs a new endpoint or extended `/api/chat` contract to provide grouped results (`groups[ {category, items[]} ]`) plus flattened list for search sync.
2. **Frontend ChatView** must render grouped bubbles: category headers + cards.
3. **Search mode auto-load** should accept aggregated results from chat (likely via new shared store, e.g. `latestChatResults.allItems`).
4. Existing caches (`SESSION_ALIGN_CACHE`, `latestSuggestCache`) can store id list for reuse; need additional structure for multi-group to ensure ordering preserved.
5. Confirm pagination / sorting expectations when injecting chat results into search view (no API roundtrip, but display should remain consistent with `format_for_chat`).

## 4. Next steps checklist

- Trace where `action.type === 'switch_to_search'` is used (currently manual via buttons); plan how chat should trigger aggregated hand-off.
- Decide whether to extend `/api/chat` or introduce `/api/chat-search` per spec.
- Map CSV fields (`VIEW_GOODS_enhanced.csv`) to grouped payload format.
- Outline frontend data store to bridge chat groups → search display (flattened list + meta for group rendering if needed).

_(Prepared by Copilot on 2025-10-23. Update this file as the implementation progresses to keep alignment with new requirements.)_

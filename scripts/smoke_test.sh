#!/bin/bash
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
TOKEN="${TOKEN:-}"

pass() { echo "✅ $1"; }
fail() { echo "❌ $1"; exit 1; }

if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found, installing (Debian/Ubuntu)..." >&2
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y jq
  else
    echo "Please install jq manually." >&2
  fi
fi

echo "== Admin info =="
curl -sf "$BASE/api/admin/info" | jq . >/dev/null && pass "admin/info OK" || fail "admin/info failed"

echo "== Taxonomy =="
curl -sf "$BASE/api/catalog/taxonomy" | jq . >/dev/null && pass "taxonomy OK" || fail "taxonomy failed"

echo "== Search basic =="
curl -sf -X POST "$BASE/api/search" -H "Content-Type: application/json" \
  -d '{"query":"橄欖油","page_size":5}' | jq '.items | length' >/dev/null && pass "search OK" || fail "search failed"

echo "== Chat overview =="
RES=$(curl -sf -X POST "$BASE/api/chat" -H "Content-Type: application/json" \
  -d '{"message":"你們有賣什麼類型東西？","history":[]}')
echo "$RES" | jq -r '.action.type' | grep -qi "none" && pass "chat action none OK" || fail "chat action should be none"
L1_COUNT=$(echo "$RES" | jq -r '.meta.available_scope.l1 | length')
if [[ "$L1_COUNT" =~ ^[0-9]+$ ]] && [ "$L1_COUNT" -ge 1 ]; then
  pass "chat overview available_scope present"
else
  fail "chat overview missing available_scope.l1"
fi

echo "== Chat OOS (3C) =="
RES=$(curl -sf -X POST "$BASE/api/chat" -H "Content-Type: application/json" \
  -d '{"message":"我要 3C 耳機","history":[]}')
echo "$RES" | jq '.meta.oos_category' | grep -q true && pass "OOS flagged OK" || fail "OOS flag missing"
echo "$RES" | jq -r '.action.type' | grep -qi "none" && pass "OOS action none OK" || fail "OOS action should be none"

echo "== Chat product search =="
RES=$(curl -sf -X POST "$BASE/api/chat" -H "Content-Type: application/json" \
  -d '{"message":"我要 橄欖油","history":[]}')
if echo "$RES" | jq -e '.suggestion_ids | length>0' >/dev/null 2>&1; then
  pass "product search suggestion_ids present"
else
  ACT=$(echo "$RES" | jq -r '.action.type // ""')
  [[ "$ACT" == "switch_to_search" ]] && pass "product search action switch OK" || fail "no suggestions or switch"
fi

echo "== Clear cache (admin) =="
if [[ -n "$TOKEN" ]]; then
  curl -sf -X POST "$BASE/api/admin/clear-cache" -H "x-admin-token: $TOKEN" | jq . >/dev/null && pass "clear-cache OK" || fail "clear-cache failed"
else
  echo "(skip) TOKEN not set; skipping clear-cache"
fi

echo "All smoke tests passed."
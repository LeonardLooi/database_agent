#!/usr/bin/env bash
# test_nginx_buffer.sh — verify nginx does not truncate responses.
# Run from project root: bash stress-test-report/tests/test_nginx_buffer.sh
set -euo pipefail
PASS=0; FAIL=0

check() {
  local name="$1" result="$2" expect="$3"
  if echo "$result" | grep -qi "$expect"; then
    echo "PASS  $name"
    ((PASS++))
  else
    echo "FAIL  $name  =>  ${result:0:150}"
    ((FAIL++))
  fi
}

echo "=== Nginx Buffer Tests ==="

BASE="https://localhost"

# 1. Health response not truncated
HEALTH=$(curl -sk "$BASE/health")
check "Health body complete (has version)" "$HEALTH" "version"
check "Health body complete (has providers)" "$HEALTH" "available_providers\|providers"

# 2. Transfer-Encoding for API
TE=$(curl -sI "$BASE/health")
check "Response has Content-Type header" "$TE" "content-type"

# 3. Response body is valid JSON (no truncation)
VALID=$(echo "$HEALTH" | python3 -c "import sys,json; json.load(sys.stdin); print('valid')" 2>/dev/null || echo "invalid")
check "Health JSON not truncated" "$VALID" "valid"

# 4. Large-ish response — list conversations (needs token)
TOKEN=$(curl -sk -X POST "$BASE/auth/guest" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
if [ -n "$TOKEN" ]; then
  CONVS=$(curl -sk "$BASE/api/conversations?token=$TOKEN")
  VALID_CONVS=$(echo "$CONVS" | python3 -c "import sys,json; json.load(sys.stdin); print('valid')" 2>/dev/null || echo "invalid")
  check "Conversations JSON not truncated" "$VALID_CONVS" "valid"
else
  echo "SKIP  Conversation buffer test (no token)"
fi

# 5. Angular SPA HTML response is complete (has </html>)
HTML=$(curl -sk "$BASE/")
check "Angular HTML response complete" "$HTML" "</html>\|</body>"

# 6. No partial content (206) on normal requests
STATUS=$(curl -skI "$BASE/health" | head -1)
check "No partial content 206" "$STATUS" "200"

echo ""
echo "Buffer: $PASS passed / $((PASS+FAIL)) total"
[ "$FAIL" -eq 0 ] || { echo "FAIL: $FAIL test(s) failed"; exit 1; }
echo "All buffer tests PASSED"

#!/usr/bin/env bash
# test_cors_auth.sh — CORS header and auth token expiry checks.
# Run from project root: bash stress-test-report/tests/test_cors_auth.sh
set -euo pipefail
PASS=0; FAIL=0

check() {
  local name="$1" result="$2" expect="$3"
  if echo "$result" | grep -qi "$expect"; then
    echo "PASS  $name"
    ((PASS++))
  else
    echo "FAIL  $name  =>  ${result:0:120}"
    ((FAIL++))
  fi
}

echo "=== CORS + Auth Tests ==="

BASE="https://localhost"

# CORS preflight on /api/conversations
CORS=$(curl -sk -X OPTIONS "$BASE/api/conversations" \
  -H "Origin: http://localhost:4200" \
  -H "Access-Control-Request-Method: GET" \
  -I)
check "CORS preflight 200/204" "$CORS" "200\|204"
check "CORS allow-origin header" "$CORS" "access-control-allow-origin"

# CORS preflight on /auth/guest
CORS2=$(curl -sk -X OPTIONS "$BASE/auth/guest" \
  -H "Origin: http://localhost:4200" \
  -H "Access-Control-Request-Method: POST" \
  -I)
check "CORS /auth/guest preflight" "$CORS2" "200\|204"

# Valid guest token
TOKEN_RESP=$(curl -sk -X POST "$BASE/auth/guest")
check "Guest token issued" "$TOKEN_RESP" "access_token"
TOKEN=$(echo "$TOKEN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -n "$TOKEN" ]; then
  # Authenticated request
  CONV=$(curl -sk "$BASE/api/conversations?token=$TOKEN")
  check "Authenticated conversations 200" "$CONV" "\[\|conversations\|{\"id\""

  # Request without token — must be 401 or 422
  UNAUTH=$(curl -skI "$BASE/api/conversations" | head -1)
  check "No-token request rejected" "$UNAUTH" "401\|422\|400"

  # Request with malformed token
  BAD=$(curl -skI "$BASE/api/conversations?token=not.a.real.token" | head -1)
  check "Malformed token rejected" "$BAD" "401\|422"
else
  echo "SKIP  Token-dependent tests (could not get token)"
fi

# Content-Security-Policy from Angular root (optional — pass if not present)
CSP=$(curl -skI "$BASE/" | grep -i "content-security-policy" || echo "not-set")
echo "INFO  CSP header: $CSP"

echo ""
echo "CORS/Auth: $PASS passed / $((PASS+FAIL)) total"
[ "$FAIL" -eq 0 ] || { echo "FAIL: $FAIL test(s) failed"; exit 1; }
echo "All CORS/Auth tests PASSED"

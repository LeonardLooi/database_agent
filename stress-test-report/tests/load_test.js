/**
 * load_test.js — k6 load test for the chatbot stack.
 * Run from project root: k6 run stress-test-report/tests/load_test.js
 * Requires Docker stack running: cd chatbot && docker compose up -d
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

export const options = {
  stages: [
    { duration: "30s", target: 20 }, // ramp up
    { duration: "1m", target: 20 }, // sustained
    { duration: "15s", target: 0 }, // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"], // p95 < 2s
    http_req_failed: ["rate<0.01"], // error rate < 1%
    guest_token_duration: ["p(95)<1000"],
    health_duration: ["p(95)<500"],
  },
};

const guestTokenDuration = new Trend("guest_token_duration");
const healthDuration = new Trend("health_duration");
const errorRate = new Rate("error_rate");

const BASE = "https://localhost";
const PARAMS = { timeout: "10s", insecureSkipTLSVerify: true };

function getGuestToken() {
  const res = http.post(`${BASE}/auth/guest`, null, PARAMS);
  guestTokenDuration.add(res.timings.duration);
  check(res, {
    "guest token 200": (r) => r.status === 200,
    "has access_token": (r) => JSON.parse(r.body).access_token !== undefined,
  }) || errorRate.add(1);
  return JSON.parse(res.body).access_token || "";
}

export default function () {
  // 1. Health check
  const health = http.get(`${BASE}/health`, PARAMS);
  healthDuration.add(health.timings.duration);
  check(health, {
    "health 200": (r) => r.status === 200,
    "health status ok": (r) => JSON.parse(r.body).status === "ok",
  }) || errorRate.add(1);

  sleep(0.1);

  // 2. Auth — get guest token
  const token = getGuestToken();

  sleep(0.1);

  // 3. List conversations (authenticated)
  const convParams = {
    ...PARAMS,
    headers: {},
  };
  const convs = http.get(
    `${BASE}/api/conversations?token=${token}`,
    convParams
  );
  check(convs, {
    "conversations 200": (r) => r.status === 200,
    "conversations array": (r) => Array.isArray(JSON.parse(r.body)),
  }) || errorRate.add(1);

  sleep(0.1);

  // 4. Angular SPA root
  const root = http.get(`${BASE}/`, PARAMS);
  check(root, {
    "SPA root 200": (r) => r.status === 200,
  }) || errorRate.add(1);

  sleep(0.5);
}

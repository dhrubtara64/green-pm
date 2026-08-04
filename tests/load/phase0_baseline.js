/**
 * S2-TEST-02 — Phase 0 load baseline
 *
 * Measures p50/p95 latency against the API gateway at 100 rps sustained.
 * Run with: k6 run tests/load/phase0_baseline.js
 * Requires: `make dev` + all services started (api-gateway on localhost:8000).
 *
 * SLOs (Phase 0 baseline):
 *   p50 < 200 ms
 *   p95 < 500 ms
 *   error rate < 1%
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ─── custom metrics ────────────────────────────────────────────────────────

const errorRate = new Rate("error_rate");
const healthLatency = new Trend("health_latency_ms", true);

// ─── options ───────────────────────────────────────────────────────────────

export const options = {
  scenarios: {
    baseline_100rps: {
      executor: "constant-arrival-rate",
      rate: 100,
      timeUnit: "1s",
      duration: "30s",
      preAllocatedVUs: 20,
      maxVUs: 50,
    },
  },
  thresholds: {
    // p50 < 200 ms, p95 < 500 ms
    http_req_duration: ["p(50)<200", "p(95)<500"],
    // error rate < 1%
    error_rate: ["rate<0.01"],
    // custom latency trend mirrors http_req_duration for the health endpoint
    health_latency_ms: ["p(50)<200", "p(95)<500"],
  },
};

// ─── config ────────────────────────────────────────────────────────────────

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

// ─── default function ──────────────────────────────────────────────────────

export default function () {
  // ── health check (lightweight, unauthenticated) ────────────────────────
  const healthRes = http.get(`${BASE_URL}/health`, {
    tags: { name: "health_check" },
  });

  const healthOk = check(healthRes, {
    "health status 200": (r) => r.status === 200,
    'health body has status ok': (r) => {
      try {
        return JSON.parse(r.body).status === "ok";
      } catch {
        return false;
      }
    },
  });

  errorRate.add(!healthOk);
  healthLatency.add(healthRes.timings.duration);
}

// ─── summary ───────────────────────────────────────────────────────────────

export function handleSummary(data) {
  const p50 = data.metrics.http_req_duration.values["p(50)"];
  const p95 = data.metrics.http_req_duration.values["p(95)"];
  const errPct = (data.metrics.error_rate.values.rate * 100).toFixed(2);
  const reqs = data.metrics.http_reqs.values.count;
  const rps = data.metrics.http_reqs.values.rate.toFixed(1);

  const sloPass = p50 < 200 && p95 < 500 && data.metrics.error_rate.values.rate < 0.01;

  const lines = [
    "",
    "╔══════════════════════════════════════════════════════╗",
    "║          Green PM — Phase 0 Load Baseline            ║",
    "╚══════════════════════════════════════════════════════╝",
    "",
    `  Requests:    ${reqs} total @ ${rps} rps`,
    `  p50 latency: ${p50.toFixed(1)} ms  (SLO < 200 ms)   ${p50 < 200 ? "✓" : "✗"}`,
    `  p95 latency: ${p95.toFixed(1)} ms  (SLO < 500 ms)   ${p95 < 500 ? "✓" : "✗"}`,
    `  Error rate:  ${errPct}%           (SLO < 1.00%)   ${parseFloat(errPct) < 1 ? "✓" : "✗"}`,
    "",
    `  Overall:     ${sloPass ? "✅ PASS — baseline SLOs met" : "❌ FAIL — one or more SLOs breached"}`,
    "",
  ];

  console.log(lines.join("\n"));

  return {
    stdout: lines.join("\n"),
  };
}

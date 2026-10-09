import http from "k6/http";
import { check } from "k6";
import { SharedArray } from "k6/data";
import exec from "k6/execution";
import type { Options } from "k6/options";

type User = { sub: string; token: string };

const users = new SharedArray("users", () => JSON.parse(open("./tokens.json")));
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const N_SUB_PER_USER = Number(__ENV.N_SUB_PER_USER);
const CATEGORIES = ["streaming", "music", "productivity", "technology"];

export const options: Options = {
  scenarios: {
    seed: {
      executor: "per-vu-iterations",
      vus: users.length,
      iterations: 1,
      maxDuration: "10m",
    },
  },
  thresholds: {
    checks: ["rate==1"],
  },
};

export default function seed() {
  const user = users[exec.vu.idInTest - 1] as User;
  const params = {
    headers: {
      Authorization: `Bearer ${user.token}`,
      "Content-Type": "application/json",
    },
  };

  for (let i = 0; i < N_SUB_PER_USER; i++) {
    const body = JSON.stringify({
      name: `loadtest-${i}`,
      cost: 50 + (i % 20) * 25,
      type: i % 5 === 0 ? "yearly" : "monthly",
      category: CATEGORIES[i % CATEGORIES.length],
      nextBillingDate: new Date(Date.UTC(2027, 11, 1 + (i % 28))).toISOString(),
      reminderTimeInAdvanced: 1,
    });
    const res = http.post(`${BASE_URL}/api/v1/subscriptions`, body, params);
    check(res, { "created 201": (r) => r.status === 201 });
  }
}

import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";
import exec from "k6/execution";
import type { Options } from "k6/options";

type User = { sub: string; token: string };
type Page = { items: { id: string }[] };

const users = new SharedArray("users", () => JSON.parse(open("./tokens.json")));
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API = `${BASE_URL}/api/v1/subscriptions`;

export const options: Options = {
  scenarios: {
    load: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 50 },
        { duration: "5m", target: 50 },
        { duration: "30s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{name:summary}": ["p(95)<2000"],
    "http_req_duration{name:list}": ["p(95)<2000"],
    "http_req_duration{name:detail}": ["p(95)<2000"],
  },
};

export default function load() {
  const user = users[(exec.vu.idInTest - 1) % users.length] as User;
  const params = (name: string) => ({
    headers: { Authorization: `Bearer ${user.token}` },
    tags: { name },
  });

  const summary = http.get(`${API}/summary`, params("summary"));
  check(summary, { "summary 200": (r) => r.status === 200 });

  const page = Math.floor(Math.random() * 10) + 1;
  const list = http.get(`${API}?page=${page}&limit=10`, params("list"));
  check(list, { "list 200": (r) => r.status === 200 });

  const items = list.status === 200 ? (list.json() as Page).items : [];
  if (items.length > 0) {
    const id = items[Math.floor(Math.random() * items.length)].id;
    const detail = http.get(`${API}/${id}`, params("detail"));
    check(detail, { "detail 200": (r) => r.status === 200 });
  }

  sleep(1 + Math.random() * 2);
}

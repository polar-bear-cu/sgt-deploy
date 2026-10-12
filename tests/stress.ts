import type { Options } from "k6/options";
import { thresholds, visit } from "./journey.ts";

export const options: Options = {
  scenarios: {
    stress: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "1m", target: 50 },
        { duration: "2m", target: 50 },
        { duration: "1m", target: 100 },
        { duration: "2m", target: 100 },
        { duration: "1m", target: 200 },
        { duration: "2m", target: 200 },
        { duration: "1m", target: 300 },
        { duration: "2m", target: 300 },
        { duration: "1m", target: 0 },
      ],
    },
  },
  thresholds,
};

export default visit;

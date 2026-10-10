import type { Options } from "k6/options";
import { thresholds, visit } from "./journey.ts";

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
  thresholds,
};

export default visit;

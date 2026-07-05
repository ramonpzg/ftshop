import { describe, expect, test } from "bun:test";
import { formatMetricValue, metricLabel } from "../../src/calculations/formatting";

describe("metricLabel", () => {
  test("title-cases each word", () => {
    expect(metricLabel("legal_move_rate")).toBe("Legal Move Rate");
  });

  test("handles a single word", () => {
    expect(metricLabel("clipping")).toBe("Clipping");
  });
});

describe("formatMetricValue", () => {
  test("keeps integers as-is", () => {
    expect(formatMetricValue(10)).toBe("10");
  });

  test("rounds floats to two decimals", () => {
    expect(formatMetricValue(0.6666666)).toBe("0.67");
  });
});

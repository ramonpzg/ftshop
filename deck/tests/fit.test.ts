/** Long-content fit guards. The stepper panels reserve fixed heights,
 * so payloads and captions have hard budgets; exceeding them clips on
 * a 1280x720 projector. These limits were set from the rendered deck,
 * not guessed. */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { NOTATION_EXAMPLE } from "../lib/chess";
import { DATASET_SHAPES } from "../lib/datasetShapes";
import { COST_ROWS, TEXT_COMPARE_FIXTURE } from "../lib/fixtures";

describe("dataset shapes are honest and fit their panel", () => {
  for (const shape of DATASET_SHAPES) {
    test(`${shape.name} payload is strictly valid JSON`, () => {
      expect(() => JSON.parse(shape.payload)).not.toThrow();
    });

    test(`${shape.name} payload and point stay inside the reserved panel`, () => {
      // The panel wraps at roughly 55 mono characters; the reserved
      // height holds nine wrapped rows. Estimate wrapped rows rather
      // than capping raw line length, since full FENs must not be
      // truncated just to fit one line.
      const wrappedRows = shape.payload
        .split("\n")
        .reduce((rows, line) => rows + Math.max(1, Math.ceil(line.length / 55)), 0);
      expect(wrappedRows).toBeLessThanOrEqual(9);
      expect(shape.point.length).toBeLessThanOrEqual(160);
    });
  }
});

describe("notation representations fit their panel", () => {
  for (const rep of NOTATION_EXAMPLE.representations) {
    test(`${rep.name} value and point fit`, () => {
      expect(rep.value.length).toBeLessThanOrEqual(80);
      expect(rep.point.length).toBeLessThanOrEqual(120);
    });
  }
});

describe("cost rows fit the stepper panel", () => {
  for (const row of COST_ROWS) {
    test(`${row.modality} cells stay short enough`, () => {
      for (const cell of [row.task, row.target]) {
        expect(cell.length).toBeLessThanOrEqual(32);
      }
      expect(row.volume.length).toBeLessThanOrEqual(20);
      for (const cell of [row.selfHosted.device, row.selfHosted.setupCost]) {
        expect(cell.length).toBeLessThanOrEqual(20);
      }
      for (const path of [row.selfHosted, row.api]) {
        // The identity is one mono line in a half-width path panel.
        expect(path.identity.length).toBeLessThanOrEqual(42);
        expect(path.outcome.length).toBeLessThanOrEqual(40);
        for (const cell of [path.latency, path.perRequestCost, path.thresholdMet]) {
          expect(cell.length).toBeLessThanOrEqual(20);
        }
      }
    });
  }
});

describe("compare fixture fits", () => {
  test("outputs and regression line fit their reserved rows", () => {
    expect(TEXT_COMPARE_FIXTURE.input.length).toBeLessThanOrEqual(70);
    expect(TEXT_COMPARE_FIXTURE.regression.length).toBeLessThanOrEqual(70);
    expect(TEXT_COMPARE_FIXTURE.metrics.length).toBeLessThanOrEqual(4);
  });

  test("scripted outputs match the accepted replay fixture", () => {
    const replay = JSON.parse(
      readFileSync(
        join(import.meta.dir, "..", "..", "artifacts", "cached", "text", "benchmark_replies.json"),
        "utf8",
      ),
    );
    expect(replay.suite_content_hash).toBe("a274c01d640a346e");
    expect(TEXT_COMPARE_FIXTURE.baseOutput).toBe(
      replay.checkpoints.base.replies["ex-10-opera-house-m7"],
    );
    expect(TEXT_COMPARE_FIXTURE.adaptedOutput).toBe(
      replay.checkpoints["gemma-chess-sft-v1"].replies["ex-10-opera-house-m7"],
    );
  });
});

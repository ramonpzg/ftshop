import { expect, test } from "@playwright/test";

/**
 * Deck acceptance checks that need a real browser. The deck's own bun
 * tests cover copy and content-length budgets, but only a rendering
 * engine can report computed font sizes; the economics slide has
 * already shipped one revision that fit geometrically while rendering
 * below readable size.
 */

const DECK = "http://localhost:3030";

// 0.7rem at the 16px root: the design system's stated type floor for
// content slides. Computed styles report unscaled canvas pixels, so
// this bound is viewport-independent.
const MIN_FONT_PX = 11;

// Economics is slide 20 on the default route (23 on the full route,
// minus the three optional slides before it).
const ECONOMICS_SLIDE = 20;

test("every fact on the economics stepper renders at or above the type floor", async ({
  page,
}) => {
  // Warm the dev server on slide 1 first; deep links into a cold
  // Slidev compile can render a stale neighbor.
  await page.goto(`${DECK}/1`);
  await page.waitForSelector(".slidev-page-1", { timeout: 30_000 });
  await page.goto(`${DECK}/${ECONOMICS_SLIDE}`);
  const scope = page.locator(`.slidev-page-${ECONOMICS_SLIDE}`);
  await expect(scope.locator("h1")).toHaveText("Economics at a target quality", {
    timeout: 15_000,
  });

  // Walk all four modalities; the assertion must hold on every step.
  for (let clicks = 0; clicks <= 3; clicks += 1) {
    const sizes = await scope
      .locator(".cost-at-target *")
      .evaluateAll((elements) =>
        elements
          .filter(
            (el) =>
              el.checkVisibility?.() !== false &&
              Array.from(el.childNodes).some(
                (node) => node.nodeType === Node.TEXT_NODE && node.textContent?.trim(),
              ),
          )
          .map((el) => ({
            text: (el.textContent ?? "").trim().slice(0, 40),
            px: Number.parseFloat(getComputedStyle(el).fontSize),
          })),
      );
    expect(sizes.length).toBeGreaterThan(0);
    for (const { text, px } of sizes) {
      expect(px, `"${text}" renders at ${px}px on click ${clicks}`).toBeGreaterThanOrEqual(
        MIN_FONT_PX,
      );
    }
    if (clicks < 3) {
      await page.keyboard.press("ArrowRight");
      await page.waitForTimeout(300);
    }
  }
});

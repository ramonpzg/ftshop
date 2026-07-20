/** Pure click-to-state mapping shared by the deck components.
 *
 * Components never own timers for educational progression. They are
 * handed the slide's click count as a prop and derive their visible
 * state through these functions, so forward and backward navigation
 * always land on the same frame and tests can drive every state
 * without a DOM.
 */

/** Index of the active step for a stepper that starts on step 0 and
 * advances one step per click. Clamped to the last step. */
export function stepIndex(clicks: number, steps: number): number {
  if (steps <= 0) return 0;
  return Math.min(Math.max(clicks, 0), steps - 1);
}

/** How many rows of a sequential reveal are visible after `clicks`
 * clicks. One row per click, capped at the row count. */
export function revealedRows(clicks: number, rows: number): number {
  return Math.min(Math.max(clicks, 0), rows);
}

/** State of the data-universe diagram: circles appear one per click
 * starting with the first visible at zero clicks, then the final
 * click splits the useful set into train and eval. */
export interface UniverseState {
  circlesVisible: number;
  splitVisible: boolean;
}

export const UNIVERSE_CIRCLES = 5;

export function universeState(clicks: number): UniverseState {
  const step = Math.min(Math.max(clicks, 0), UNIVERSE_CIRCLES);
  return {
    circlesVisible: Math.min(step + 1, UNIVERSE_CIRCLES),
    splitVisible: step >= UNIVERSE_CIRCLES,
  };
}

/** OutcomeCompare reveal: the matched input and both column labels
 * are on from click zero, the base column lands first, then the
 * adapted column together with its deltas and the regression row. */
export interface CompareState {
  baseVisible: boolean;
  adaptedVisible: boolean;
}

export function compareState(clicks: number): CompareState {
  return { baseVisible: clicks >= 1, adaptedVisible: clicks >= 2 };
}

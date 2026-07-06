/** Pure ordering and navigation math for frame-based slides. */

export interface SlideFrame {
  id: string;
  name: string;
  x: number;
  y: number;
}

const numericCompare = new Intl.Collator(undefined, { numeric: true }).compare;

/**
 * Presentation order for the frames on a page. Names win (numeric-aware,
 * so "Slide 2" comes before "Slide 10"), position breaks ties so unnamed
 * frames still get a stable left-to-right, top-to-bottom order.
 */
export function orderSlides(frames: SlideFrame[]): SlideFrame[] {
  return [...frames].sort((a, b) => {
    const byName = numericCompare(a.name, b.name);
    if (byName !== 0) return byName;
    if (a.x !== b.x) return a.x - b.x;
    return a.y - b.y;
  });
}

/** Clamped step through the deck. No wrap-around: past the last slide stays on the last. */
export function stepSlideIndex(current: number, total: number, delta: -1 | 1): number {
  if (total <= 0) return -1;
  const base = current < 0 ? (delta === 1 ? -1 : total) : current;
  return Math.min(total - 1, Math.max(0, base + delta));
}

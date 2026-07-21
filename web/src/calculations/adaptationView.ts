/** Pure display helpers for the adaptation evidence chain. No I/O. */

/** The first eight hex characters of a content or position-set hash:
 * enough to compare two on screen, short enough to read aloud. */
export function shortHash(hash: string | null | undefined): string {
  if (!hash) return "-";
  return hash.slice(0, 8);
}

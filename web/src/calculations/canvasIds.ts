/** Deterministic tldraw record ids for the workshop's structural content.
 * Pure string construction so both the browser and the sync server can
 * compute them. The formats match tldraw's PageRecordType.createId and
 * createShapeId conventions. */

export function pageIdForSlug(slug: string): string {
  return `page:${slug}`;
}

export function seedShapeId(slug: string, index: number): string {
  return `shape:seed-${slug}-${index}`;
}

export function seedPromptShapeId(slug: string, index: number): string {
  return `shape:seed-${slug}-${index}-prompt`;
}

export function modalityPanelShapeId(slug: string): string {
  return `shape:modality-panel-${slug}`;
}

export const DECK_SHAPE_ID = "shape:deck-panel";

export const ADAPTATION_SHAPE_ID = "shape:adaptation-panel";

export const DOCUMENT_RECORD_ID = "document:document";

/**
 * A valid fractional index for the nth generated sibling. The integer
 * part's leading letter encodes its digit count ('a' one digit, 'b' two,
 * 'c' three), which keeps every generated key well formed for tldraw's
 * index validator without pulling in the indexing library.
 */
export function seedIndex(n: number): string {
  if (n < 0 || !Number.isInteger(n)) throw new Error(`seed index out of range: ${n}`);
  if (n < 10) return `a${n}`;
  if (n < 100) return `b${n}`;
  if (n < 1000) return `c${n}`;
  throw new Error(`seed index out of range: ${n}`);
}

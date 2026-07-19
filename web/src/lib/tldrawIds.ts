/** Typed wrappers over the pure id calculations, for code that talks to
 * a live tldraw Editor. */

import type { TLPageId } from "tldraw";
import { pageIdForSlug as pageIdStringForSlug } from "../calculations/canvasIds";

export function pageIdForSlug(slug: string): TLPageId {
  return pageIdStringForSlug(slug) as TLPageId;
}

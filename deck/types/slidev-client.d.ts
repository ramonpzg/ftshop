/** Minimal typed surface for the one Slidev client API the deck uses.
 *
 * tsconfig `paths` resolves `@slidev/client` here for type checking
 * only; Vite resolves the real package at build and dev time. The
 * package ships .ts source that depends on Slidev's injected build
 * globals, so vue-tsc cannot check against it directly.
 */
import type { ComputedRef } from "vue";

export interface DeckSlideRoute {
  meta?: { slide?: { frontmatter?: Record<string, unknown> } };
}

export function useNav(): {
  currentPage: number;
  currentSlideRoute: ComputedRef<DeckSlideRoute | undefined>;
};

/** Style switch for the deck. Two styles share every slide, layout,
 * click, and motion rule; only tokens and type change.
 *
 * - paper (default): light scoresheet, IBM Plex.
 * - chalk: near-black ground, light ink, Shantell Sans (the family
 *   tldraw uses for its draw style), dark Shiki palette. Matches the
 *   whiteboard's energy without importing its hand-drawn shapes.
 *
 * Selected at server or build start: VITE_DECK_STYLE=chalk, wired as
 * `just deck chalk` and the dev:chalk / build:chalk scripts. The
 * chalk fonts load only when selected.
 */
import { defineAppSetup } from "@slidev/types";

export default defineAppSetup(() => {
  if (import.meta.env.VITE_DECK_STYLE === "chalk") {
    document.documentElement.classList.add("style-chalk");
    import("@fontsource/shantell-sans/400.css");
    import("@fontsource/shantell-sans/500.css");
    import("@fontsource/shantell-sans/700.css");
  }
});

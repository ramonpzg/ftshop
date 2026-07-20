/** Light Shiki theme to match the paper ground. github-light rather
 * than the muted vitesse palettes: token contrast has to survive a
 * washed-out projector. */
import { defineShikiSetup } from "@slidev/types";

export default defineShikiSetup(() => ({
  themes: {
    dark: "github-dark",
    light: "github-light",
  },
}));

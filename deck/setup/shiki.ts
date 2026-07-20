/** Light Shiki theme to match the paper ground; the default dark
 * token palette has no contrast on it. */
import { defineShikiSetup } from "@slidev/types";

export default defineShikiSetup(() => ({
  themes: {
    dark: "vitesse-dark",
    light: "vitesse-light",
  },
}));

/** Mermaid theming for the fine-tuning method diagrams. Colors come
 * from the same palette as style.css; VITE_DECK_STYLE picks the set,
 * mirroring setup/main.ts. Trained/frozen node classes are styled in
 * style.css on top of this base. */
import { defineMermaidSetup } from "@slidev/types";

export default defineMermaidSetup(() => {
  const chalk = import.meta.env.VITE_DECK_STYLE === "chalk";
  const accent = chalk ? "#7a9bff" : "#1f4fd8";
  const faint = chalk ? "#85817a" : "#8a8377";
  const shared = {
    fontSize: "15px",
  };
  return {
    theme: "base",
    // The SVG lives in a shadow root, so the deck stylesheet cannot
    // reach it. Trained/frozen node classes (assigned per diagram with
    // `class X trained`) are styled here instead.
    themeCSS: `
      .trained rect { stroke: ${accent} !important; stroke-width: 2.5px !important; }
      .trained .nodeLabel, .trained .nodeLabel p { color: ${accent} !important; font-weight: 600; }
      .frozen rect { stroke-dasharray: 5 4; }
      .frozen .nodeLabel, .frozen .nodeLabel p, .frozen .cluster-label p { color: ${faint} !important; }
    `,
    themeVariables: chalk
      ? {
          ...shared,
          fontFamily: "Shantell Sans, IBM Plex Sans, sans-serif",
          background: "#17171a",
          primaryColor: "#222227",
          primaryTextColor: "#f3f1ec",
          primaryBorderColor: "#b9b5ac",
          lineColor: "#b9b5ac",
          secondaryColor: "#17171a",
          tertiaryColor: "#17171a",
          clusterBkg: "#17171a",
          clusterBorder: "#3a3a41",
          edgeLabelBackground: "#17171a",
        }
      : {
          ...shared,
          fontFamily: "IBM Plex Sans, sans-serif",
          background: "#f6f4ef",
          primaryColor: "#fdfcf9",
          primaryTextColor: "#191713",
          primaryBorderColor: "#5c564c",
          lineColor: "#5c564c",
          secondaryColor: "#f6f4ef",
          tertiaryColor: "#f6f4ef",
          clusterBkg: "#f6f4ef",
          clusterBorder: "#d9d3c7",
          edgeLabelBackground: "#f6f4ef",
        },
  };
});

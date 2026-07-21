/** Static definition of the five workshop pages. Shared shape with api/src/euro_chess_studio/calculations/pages.py. */

export type Modality = "meta" | "text" | "image" | "audio" | "video";

export interface PageDef {
  slug: string;
  title: string;
  modality: Modality;
  order: number;
  showInTabs?: boolean;
}

export const PAGES: PageDef[] = [
  {
    slug: "presentation",
    title: "Presentation",
    modality: "meta",
    order: 0,
    showInTabs: false,
  },
  { slug: "chess-machine", title: "Building a Chess Machine", modality: "text", order: 1 },
  { slug: "painting-pieces", title: "Painting Our Pieces", modality: "image", order: 2 },
  { slug: "board-sound", title: "Giving the Board Sound", modality: "audio", order: 3 },
  {
    slug: "real-world-video",
    title: "Video of the Real-World Use Case",
    modality: "video",
    order: 4,
  },
];

// Keep the presentation page and embedded deck as an emergency fallback,
// without putting a redundant destination in the attendee-facing tabs.
export const PAGE_TABS = PAGES.filter((page) => page.showInTabs !== false);

import {
  createShapeId,
  type Editor,
  PageRecordType,
  type TLDefaultColorStyle,
  type TLPageId,
  type TLShapePartial,
  toRichText,
} from "tldraw";
import { getPageSeedShapes, type SeedShape } from "../calculations/pageSeeds";
import { PAGES } from "../lib/pages";

export function pageIdForSlug(slug: string): TLPageId {
  return PageRecordType.createId(slug);
}

function seedShapeId(slug: string, index: number) {
  return createShapeId(`seed-${slug}-${index}`);
}

function modalityPanelShapeId(slug: string) {
  return createShapeId(`modality-panel-${slug}`);
}

function notebookShapeId(slug: string) {
  return createShapeId(`notebook-panel-${slug}`);
}

function toShapePartials(
  shape: SeedShape,
  pageId: TLPageId,
  slug: string,
  index: number,
): TLShapePartial[] {
  const id = seedShapeId(slug, index);
  if (shape.kind === "heading") {
    return [
      {
        id,
        type: "text" as const,
        parentId: pageId,
        x: shape.x,
        y: shape.y,
        props: {
          richText: toRichText(shape.text),
          size: (index === 0 ? "xl" : "m") as "xl" | "m",
          w: 820,
        },
      },
    ];
  }
  if (shape.kind === "frame") {
    const promptId = createShapeId(`seed-${slug}-${index}-prompt`);
    return [
      {
        id,
        type: "frame" as const,
        parentId: pageId,
        x: shape.x,
        y: shape.y,
        props: { w: shape.w, h: shape.h, name: shape.name },
      },
      {
        id: promptId,
        type: "text" as const,
        parentId: id,
        x: 80,
        y: 80,
        props: {
          richText: toRichText(shape.prompt),
          size: "m" as const,
          w: shape.w - 160,
        },
      },
    ];
  }
  return [
    {
      id,
      type: "note" as const,
      parentId: pageId,
      x: shape.x,
      y: shape.y,
      props: {
        richText: toRichText(shape.text),
        color: (shape.color ?? "yellow") as TLDefaultColorStyle,
      },
    },
  ];
}

const MODALITY_PANEL_MODALITIES = new Set(["image", "audio", "video"]);

/**
 * Ensures all five workshop pages exist with their starter content.
 * Safe to call on every mount: pages and shapes are only created once,
 * keyed by deterministic ids, so a presenter's edits are never overwritten.
 * Jumps to the Presentation page only when something was freshly seeded;
 * a restored canvas keeps whatever page the document was on.
 */
export function ensurePagesSeeded(editor: Editor): boolean {
  let seededAnything = false;
  for (const page of PAGES) {
    const pageId = pageIdForSlug(page.slug);
    const exists = editor.getPages().some((p) => p.id === pageId);
    if (!exists) {
      editor.createPage({ id: pageId, name: page.title });
      seededAnything = true;
    }
    if (editor.getPageShapeIds(pageId).size === 0) {
      const seeds = getPageSeedShapes(page.slug);
      const shapes: TLShapePartial[] = seeds.flatMap((seed, index) =>
        toShapePartials(seed, pageId, page.slug, index),
      );

      if (MODALITY_PANEL_MODALITIES.has(page.modality)) {
        shapes.push({
          id: modalityPanelShapeId(page.slug),
          type: "modality-panel" as const,
          parentId: pageId,
          // Below the seeded note rows, which now reach to roughly y=1060.
          x: 0,
          y: 1200,
          props: { modality: page.modality, pageSlug: page.slug },
        });
      }

      if (page.modality !== "meta") {
        shapes.push({
          id: notebookShapeId(page.slug),
          type: "notebook-panel" as const,
          parentId: pageId,
          // Below the explainer frames, above the workspace band at y=1500.
          x: 1400,
          y: 800,
          props: { w: 1200, h: 650, pageSlug: page.slug },
        });
      }

      editor.createShapes(shapes);
      seededAnything = true;
    }
  }
  if (seededAnything) {
    editor.setCurrentPage(pageIdForSlug(PAGES[0].slug));
    // Drop the empty default page a brand-new store starts with. Pages a
    // presenter added on purpose have content, so they survive.
    for (const page of editor.getPages()) {
      const isWorkshopPage = PAGES.some((p) => pageIdForSlug(p.slug) === page.id);
      if (!isWorkshopPage && editor.getPageShapeIds(page.id).size === 0) {
        editor.deletePage(page.id);
      }
    }
  }
  return seededAnything;
}

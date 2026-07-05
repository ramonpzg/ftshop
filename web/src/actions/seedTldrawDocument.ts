import { createShapeId, type Editor, PageRecordType, type TLPageId, toRichText } from "tldraw";
import { getPageSeedShapes, type SeedShape } from "../calculations/pageSeeds";
import { PAGES } from "../lib/pages";

export function pageIdForSlug(slug: string): TLPageId {
  return PageRecordType.createId(slug);
}

function seedShapeId(slug: string, index: number) {
  return createShapeId(`seed-${slug}-${index}`);
}

function toShapePartial(shape: SeedShape, pageId: TLPageId, slug: string, index: number) {
  const id = seedShapeId(slug, index);
  if (shape.kind === "heading") {
    return {
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
    };
  }
  return {
    id,
    type: "note" as const,
    parentId: pageId,
    x: shape.x,
    y: shape.y,
    props: {
      richText: toRichText(shape.text),
      color: shape.color ?? "yellow",
    },
  };
}

/**
 * Ensures all five workshop pages exist with their starter content.
 * Safe to call on every mount: pages and shapes are only created once,
 * keyed by deterministic ids, so a presenter's edits are never overwritten.
 */
export function ensurePagesSeeded(editor: Editor): void {
  for (const page of PAGES) {
    const pageId = pageIdForSlug(page.slug);
    const exists = editor.getPages().some((p) => p.id === pageId);
    if (!exists) {
      editor.createPage({ id: pageId, name: page.title });
    }
    if (editor.getPageShapeIds(pageId).size === 0) {
      const seeds = getPageSeedShapes(page.slug);
      editor.createShapes(
        seeds.map((seed, index) => toShapePartial(seed, pageId, page.slug, index)),
      );
    }
  }
  editor.setCurrentPage(pageIdForSlug(PAGES[0].slug));
}

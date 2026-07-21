/** Builders for complete tldraw records, usable without an editor.
 *
 * The canvas migrations run on the sync server, where no tldraw Editor
 * exists to fill in shape prop defaults, so every builder here emits the
 * full record its validator expects. The defaults mirror tldraw 5.1.1's
 * shape utils; the migration tests load built records into a real store
 * to prove they validate.
 */

import { PRESENTER_OWNER } from "./canvasOwnership";
import { type RichTextDoc, richTextFromLines } from "./richText";

export interface CanvasRecord {
  id: string;
  typeName: string;
  [key: string]: unknown;
}

export function buildPageRecord(slug: string, name: string, index: string): CanvasRecord {
  return {
    id: `page:${slug}`,
    typeName: "page",
    name,
    index,
    meta: { owner: PRESENTER_OWNER },
  };
}

interface ShapeBase {
  id: string;
  parentId: string;
  index: string;
  x: number;
  y: number;
}

function shapeRecord(base: ShapeBase, type: string, props: Record<string, unknown>): CanvasRecord {
  return {
    id: base.id,
    typeName: "shape",
    type,
    parentId: base.parentId,
    index: base.index,
    x: base.x,
    y: base.y,
    rotation: 0,
    isLocked: false,
    opacity: 1,
    meta: { owner: PRESENTER_OWNER },
    props,
  };
}

export function buildNoteRecord(
  base: ShapeBase,
  text: string,
  color: string = "yellow",
): CanvasRecord {
  return shapeRecord(base, "note", {
    color,
    richText: richTextFromLines(text) satisfies RichTextDoc,
    size: "m",
    font: "draw",
    align: "middle",
    verticalAlign: "middle",
    labelColor: "black",
    growY: 0,
    fontSizeAdjustment: 1,
    url: "",
    scale: 1,
    textFirstEditedBy: null,
  });
}

export function buildTextRecord(
  base: ShapeBase,
  text: string,
  options: { size: "xl" | "m"; w: number },
): CanvasRecord {
  return shapeRecord(base, "text", {
    color: "black",
    size: options.size,
    w: options.w,
    font: "draw",
    textAlign: "start",
    autoSize: true,
    scale: 1,
    richText: richTextFromLines(text),
  });
}

export function buildFrameRecord(
  base: ShapeBase,
  options: { w: number; h: number; name: string },
): CanvasRecord {
  return shapeRecord(base, "frame", {
    w: options.w,
    h: options.h,
    name: options.name,
    color: "black",
  });
}

export function buildModalityPanelRecord(
  base: ShapeBase,
  options: { modality: string; pageSlug: string },
): CanvasRecord {
  return shapeRecord(base, "modality-panel", {
    w: 900,
    h: 420,
    modality: options.modality,
    pageSlug: options.pageSlug,
  });
}

export function buildDeckPanelRecord(base: ShapeBase, url: string): CanvasRecord {
  return shapeRecord(base, "deck-panel", { w: 1440, h: 850, url });
}

export function buildAdaptationPanelRecord(base: ShapeBase, pageSlug: string): CanvasRecord {
  return shapeRecord(base, "adaptation-panel", { w: 1400, h: 1040, pageSlug });
}

export function buildDocumentRecord(): CanvasRecord {
  return {
    id: "document:document",
    typeName: "document",
    gridSize: 10,
    name: "",
    meta: {},
  };
}

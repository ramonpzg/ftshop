/** Presenter-side publication of navigation targets. */

import type { Editor, TLShapeId } from "tldraw";
import { bringToPresenterView, type PresenterState } from "../data/api";
import { pageIdForSlug } from "../lib/tldrawIds";
import { PAGES } from "../lib/pages";

function currentWorkshopPageSlug(editor: Editor): string {
  const currentId = editor.getCurrentPageId();
  const page = PAGES.find((p) => pageIdForSlug(p.slug) === currentId);
  return page?.slug ?? PAGES[0].slug;
}

/**
 * Publishes the presenter's current view: page plus the exact camera
 * bounds on screen right now. Attendees zoom to the same region instead
 * of a whole-page fit.
 */
export function bringEveryoneHere(editor: Editor): Promise<PresenterState> {
  const viewport = editor.getViewportPageBounds();
  return bringToPresenterView({
    pageSlug: currentWorkshopPageSlug(editor),
    bounds: { x: viewport.x, y: viewport.y, w: viewport.w, h: viewport.h },
  });
}

/**
 * Publishes a slide frame as the shared target. Called by the slide
 * controls while presenter mode is live, so Prev/Next move the room.
 * The frame's bounds ride along as the fallback if the frame is later
 * deleted.
 */
export function broadcastSlideTarget(editor: Editor, frameId: string): Promise<PresenterState> {
  const bounds = editor.getShapePageBounds(frameId as TLShapeId);
  return bringToPresenterView({
    pageSlug: currentWorkshopPageSlug(editor),
    frameId,
    bounds: bounds ? { x: bounds.x, y: bounds.y, w: bounds.w, h: bounds.h } : undefined,
  });
}

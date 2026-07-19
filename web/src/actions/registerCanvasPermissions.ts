/** Enforces the canvas ownership rules inside a client.
 *
 * tldraw store side effects intercept every local mutation before it
 * reaches the document (and therefore before it syncs): blocked changes
 * return the previous record, blocked deletes return false, and a
 * created record the actor was never allowed to make is removed in the
 * same transaction. Remote changes (source "remote") pass through
 * untouched; the other client already enforced its own rules, and
 * fighting the server's authoritative stream would corrupt the room.
 *
 * Every shape created locally is stamped with its owner through
 * getInitialMetaForShape, which is what makes the rules in
 * calculations/canvasOwnership.ts checkable at all.
 */

import type { Editor } from "tldraw";
import {
  type CanvasActor,
  canChangeRecord,
  canCreateRecord,
  canDeleteRecord,
  ownerForNewShape,
} from "../calculations/canvasOwnership";

export function registerCanvasPermissions(
  editor: Editor,
  getActor: () => CanvasActor,
): () => void {
  const disposers = [
    editor.sideEffects.registerBeforeChangeHandler("shape", (prev, next, source) => {
      if (source !== "user") return next;
      return canChangeRecord(getActor(), prev, next) ? next : prev;
    }),
    editor.sideEffects.registerBeforeDeleteHandler("shape", (shape, source) => {
      if (source !== "user") return;
      if (!canDeleteRecord(getActor(), shape)) return false;
    }),
    editor.sideEffects.registerAfterCreateHandler("shape", (shape, source) => {
      if (source !== "user") return;
      if (!canCreateRecord(getActor(), shape)) editor.store.remove([shape.id]);
    }),
    editor.sideEffects.registerBeforeChangeHandler("page", (prev, next, source) => {
      if (source !== "user") return next;
      return canChangeRecord(getActor(), prev, next) ? next : prev;
    }),
    editor.sideEffects.registerBeforeDeleteHandler("page", (page, source) => {
      if (source !== "user") return;
      if (!canDeleteRecord(getActor(), page)) return false;
    }),
    editor.sideEffects.registerAfterCreateHandler("page", (page, source) => {
      if (source !== "user") return;
      if (!canCreateRecord(getActor(), page)) editor.store.remove([page.id]);
    }),
    editor.sideEffects.registerBeforeChangeHandler("document", (prev, next, source) => {
      if (source !== "user") return next;
      return canChangeRecord(getActor(), prev, next) ? next : prev;
    }),
    editor.sideEffects.registerBeforeDeleteHandler("asset", (asset, source) => {
      if (source !== "user") return;
      if (!canDeleteRecord(getActor(), asset)) return false;
    }),
  ];

  const previousGetInitialMeta = editor.getInitialMetaForShape;
  editor.getInitialMetaForShape = () => ({ owner: ownerForNewShape(getActor()) });

  return () => {
    for (const dispose of disposers) dispose();
    editor.getInitialMetaForShape = previousGetInitialMeta;
  };
}

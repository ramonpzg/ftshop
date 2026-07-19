/** Explicit ownership rules for the shared canvas.
 *
 * Every document record has an owner recorded in its meta, not inferred
 * from colors or labels. The presenter owns the workshop's structure:
 * pages, seeded headings and notes, slide frames, the deck panel, the
 * modality panels. An attendee owns their workspace shape and anything
 * they draw themselves.
 *
 * These rules are enforced in every normal client through tldraw store
 * side effects (see actions/registerCanvasPermissions.ts) and coarsely at
 * the sync server, which refuses writes from sessions that never
 * identified themselves. There is no authentication in v0, so a hostile
 * hand-rolled client is out of scope; that boundary is documented, not
 * hidden.
 */

export const PRESENTER_OWNER = "presenter";

export interface CanvasActor {
  isPresenter: boolean;
  userId: string | null;
}

interface RecordLike {
  id: string;
  typeName: string;
  meta?: { owner?: unknown; [key: string]: unknown };
  isLocked?: boolean;
}

/** Records with no explicit owner are treated as presenter-owned. That
 * protective default means content authored before ownership existed can
 * never be edited away by an attendee. */
export function recordOwner(record: RecordLike): string {
  const owner = record.meta?.owner;
  return typeof owner === "string" && owner.length > 0 ? owner : PRESENTER_OWNER;
}

export function ownerForNewShape(actor: CanvasActor): string {
  if (actor.isPresenter) return PRESENTER_OWNER;
  return actor.userId ?? PRESENTER_OWNER;
}

function actorOwns(actor: CanvasActor, record: RecordLike): boolean {
  return actor.userId !== null && recordOwner(record) === actor.userId;
}

/** Document-scope record types an attendee may never create, change, or
 * delete: the page list and the document record are workshop structure. */
const STRUCTURAL_TYPE_NAMES = new Set(["page", "document"]);

export function canCreateRecord(actor: CanvasActor, record: RecordLike): boolean {
  if (actor.isPresenter) return true;
  if (STRUCTURAL_TYPE_NAMES.has(record.typeName)) return false;
  // Uploads must work for everyone: dropping an image creates an asset.
  if (record.typeName === "asset") return true;
  return actorOwns(actor, record);
}

export function canChangeRecord(actor: CanvasActor, before: RecordLike, after: RecordLike): boolean {
  if (actor.isPresenter) return true;
  if (STRUCTURAL_TYPE_NAMES.has(before.typeName)) return false;
  // tldraw itself updates asset records (for example resolved video
  // dimensions); blocking that breaks everyone's media for no gain.
  if (before.typeName === "asset") return true;
  if (!actorOwns(actor, before)) return false;
  // Owning a shape does not include reassigning it or flipping its lock.
  if (recordOwner(after) !== recordOwner(before)) return false;
  if ((after.isLocked ?? false) !== (before.isLocked ?? false)) return false;
  return true;
}

export function canDeleteRecord(actor: CanvasActor, record: RecordLike): boolean {
  if (actor.isPresenter) return true;
  if (STRUCTURAL_TYPE_NAMES.has(record.typeName)) return false;
  if (record.typeName === "asset") return false;
  return actorOwns(actor, record);
}

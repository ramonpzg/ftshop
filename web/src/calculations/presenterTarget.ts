/** Pure decisions for remote presenter navigation.
 *
 * The design: the presenter publishes a navigation target of page slug,
 * optional frame id, and the camera bounds captured at click time, plus
 * a server-side monotonically increasing revision. Clients order on the
 * revision alone. tldraw's public zoomToBounds/zoomToFit APIs apply the
 * result; this module only decides what to apply.
 */

export interface PresenterTargetBounds {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PresenterSyncState {
  mode: string;
  locked: boolean;
  revision: number;
  active_page_slug: string | null;
  target_frame_id: string | null;
  target_bounds: PresenterTargetBounds | null;
}

/**
 * Whether a polled state should be applied, given the last revision this
 * client applied (null before the first completed poll).
 *
 * The first poll always applies when the room is in a driven mode; that
 * is what brings a late joiner to the presenter's current view. After
 * that only strictly newer revisions apply, so repeated polls no-op and
 * a slow response can never roll the camera back to an older target.
 */
export function shouldApplyPresenterState(
  state: PresenterSyncState,
  lastAppliedRevision: number | null,
): boolean {
  if (lastAppliedRevision === null) return state.mode !== "idle";
  return state.revision > lastAppliedRevision;
}

/** What the canvas document can answer about pages and frames, kept
 * minimal so tests can fake it without an editor. */
export interface CanvasDocView {
  hasPage(pageSlug: string): boolean;
  /** Page-space bounds of the frame, or null when the frame is missing
   * or lives on a different page. */
  frameBounds(frameId: string, pageSlug: string): PresenterTargetBounds | null;
}

export type PresenterViewResolution =
  | { kind: "bounds"; pageSlug: string; bounds: PresenterTargetBounds; inset: number; notice: null }
  | { kind: "page"; pageSlug: string; notice: string | null }
  | { kind: "workspace" }
  | { kind: "none"; notice: string | null };

export function resolvePresenterView(
  state: PresenterSyncState,
  doc: CanvasDocView,
): PresenterViewResolution {
  if (state.mode === "workspaces") return { kind: "workspace" };
  if (state.mode !== "presenter" || !state.active_page_slug) {
    return { kind: "none", notice: null };
  }

  const pageSlug = state.active_page_slug;
  if (!doc.hasPage(pageSlug)) {
    return { kind: "none", notice: "Presenter page missing. Staying here." };
  }

  if (state.target_frame_id) {
    const frame = doc.frameBounds(state.target_frame_id, pageSlug);
    if (frame) return { kind: "bounds", pageSlug, bounds: frame, inset: 48, notice: null };
    if (state.target_bounds) {
      return { kind: "bounds", pageSlug, bounds: state.target_bounds, inset: 0, notice: null };
    }
    return { kind: "page", pageSlug, notice: "Presenter frame missing. Showing the page." };
  }

  if (state.target_bounds) {
    return { kind: "bounds", pageSlug, bounds: state.target_bounds, inset: 0, notice: null };
  }
  return { kind: "page", pageSlug, notice: null };
}

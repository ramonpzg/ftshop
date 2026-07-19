import { describe, expect, test } from "bun:test";
import {
  type CanvasDocView,
  type PresenterSyncState,
  resolvePresenterView,
  shouldApplyPresenterState,
} from "../../src/calculations/presenterTarget";

function state(overrides: Partial<PresenterSyncState> = {}): PresenterSyncState {
  return {
    mode: "presenter",
    locked: false,
    revision: 5,
    active_page_slug: "presentation",
    target_frame_id: null,
    target_bounds: null,
    ...overrides,
  };
}

const BOUNDS = { x: 0, y: 1400, w: 1600, h: 900 };

function doc(overrides: Partial<CanvasDocView> = {}): CanvasDocView {
  return {
    hasPage: () => true,
    frameBounds: () => null,
    ...overrides,
  };
}

describe("shouldApplyPresenterState", () => {
  test("a late joiner applies the current driven state on its first poll", () => {
    expect(shouldApplyPresenterState(state({ mode: "presenter" }), null)).toBe(true);
    expect(shouldApplyPresenterState(state({ mode: "workspaces" }), null)).toBe(true);
  });

  test("an idle room does not move a fresh client", () => {
    expect(shouldApplyPresenterState(state({ mode: "idle" }), null)).toBe(false);
  });

  test("repeated polls with the same revision do nothing", () => {
    expect(shouldApplyPresenterState(state({ revision: 5 }), 5)).toBe(false);
  });

  test("a slow poll carrying an older revision never rolls the camera back", () => {
    expect(shouldApplyPresenterState(state({ revision: 4 }), 5)).toBe(false);
  });

  test("a newer revision applies", () => {
    expect(shouldApplyPresenterState(state({ revision: 6 }), 5)).toBe(true);
  });
});

describe("resolvePresenterView", () => {
  test("a live frame wins and gets the slide inset", () => {
    const view = resolvePresenterView(
      state({ target_frame_id: "shape:f", target_bounds: { x: 1, y: 2, w: 3, h: 4 } }),
      doc({ frameBounds: () => BOUNDS }),
    );
    expect(view).toEqual({
      kind: "bounds",
      pageSlug: "presentation",
      bounds: BOUNDS,
      inset: 48,
      notice: null,
    });
  });

  test("a deleted frame falls back to the captured bounds", () => {
    const view = resolvePresenterView(
      state({ target_frame_id: "shape:gone", target_bounds: BOUNDS }),
      doc(),
    );
    expect(view.kind).toBe("bounds");
    if (view.kind === "bounds") {
      expect(view.bounds).toEqual(BOUNDS);
      expect(view.inset).toBe(0);
    }
  });

  test("a deleted frame with no bounds degrades to the page with a concise notice", () => {
    const view = resolvePresenterView(state({ target_frame_id: "shape:gone" }), doc());
    expect(view).toEqual({
      kind: "page",
      pageSlug: "presentation",
      notice: "Presenter frame missing. Showing the page.",
    });
  });

  test("bounds without a frame zoom exactly to the presenter's viewport", () => {
    const view = resolvePresenterView(state({ target_bounds: BOUNDS }), doc());
    expect(view).toEqual({
      kind: "bounds",
      pageSlug: "presentation",
      bounds: BOUNDS,
      inset: 0,
      notice: null,
    });
  });

  test("a missing page stays put instead of rendering a blank canvas", () => {
    const view = resolvePresenterView(state(), doc({ hasPage: () => false }));
    expect(view).toEqual({ kind: "none", notice: "Presenter page missing. Staying here." });
  });

  test("workspaces mode resolves to the attendee's own workspace", () => {
    expect(resolvePresenterView(state({ mode: "workspaces" }), doc())).toEqual({
      kind: "workspace",
    });
  });

  test("a frame on the wrong page is treated as missing", () => {
    const view = resolvePresenterView(
      state({ target_frame_id: "shape:f", target_bounds: BOUNDS }),
      doc({ frameBounds: () => null }),
    );
    expect(view.kind).toBe("bounds");
  });
});

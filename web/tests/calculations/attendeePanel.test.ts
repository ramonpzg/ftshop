import { describe, expect, test } from "bun:test";
import {
  attendeePanelCollapsed,
  PRESENTATION_PAGE_ID,
} from "../../src/calculations/attendeePanel";

describe("attendeePanelCollapsed", () => {
  test("collapses on the presentation page so the embedded deck stays visible", () => {
    expect(attendeePanelCollapsed(PRESENTATION_PAGE_ID, false)).toBe(true);
  });

  test("an explicit expand overrides the collapse", () => {
    expect(attendeePanelCollapsed(PRESENTATION_PAGE_ID, true)).toBe(false);
  });

  test("stays open on every other page", () => {
    expect(attendeePanelCollapsed("page:chess-machine", false)).toBe(false);
    expect(attendeePanelCollapsed(null, false)).toBe(false);
  });
});

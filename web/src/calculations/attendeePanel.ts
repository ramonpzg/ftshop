export const PRESENTATION_PAGE_ID = "page:presentation";

/**
 * The attendee panel is a fixed overlay on the right edge, which is
 * exactly where the embedded deck sits on the presentation page. It
 * collapses to a pill there so it cannot cover the slides; expanding
 * is an explicit override that lasts until the page changes.
 */
export function attendeePanelCollapsed(
  currentPageId: string | null,
  expandedOverride: boolean,
): boolean {
  return currentPageId === PRESENTATION_PAGE_ID && !expandedOverride;
}

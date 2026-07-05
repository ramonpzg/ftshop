/** Pure layout math for placing generated workspace shapes on a tldraw page. */

export interface WorkspacePosition {
  x: number;
  y: number;
}

const WORKSPACE_WIDTH = 900;
const WORKSPACE_HEIGHT = 560;
const GUTTER = 80;
const COLUMNS = 3;

/**
 * Grid position for the Nth workspace created on a page, wrapping to a new
 * row every COLUMNS workspaces. Deterministic so re-joining the same index
 * always lands in the same place.
 */
export function computeWorkspacePosition(index: number): WorkspacePosition {
  if (index < 0 || !Number.isInteger(index)) {
    throw new Error(`workspace index must be a non-negative integer, got ${index}`);
  }
  const column = index % COLUMNS;
  const row = Math.floor(index / COLUMNS);
  return {
    x: column * (WORKSPACE_WIDTH + GUTTER),
    y: row * (WORKSPACE_HEIGHT + GUTTER),
  };
}

export const WORKSPACE_DIMENSIONS = { width: WORKSPACE_WIDTH, height: WORKSPACE_HEIGHT };

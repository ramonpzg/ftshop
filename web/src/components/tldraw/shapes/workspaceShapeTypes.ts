import { T, type TLShape } from "tldraw";

export interface WorkspaceShapeProps {
  w: number;
  h: number;
  workspaceId: string;
  userId: string;
  userName: string;
  pageSlug: string;
}

// tldraw 5 custom-shape typing: augmenting this map teaches every editor
// API (createShapes, getShape, ...) about the shape type.
declare module "@tldraw/tlschema" {
  interface TLGlobalShapePropsMap {
    workspace: WorkspaceShapeProps;
  }
}

export type WorkspaceShape = TLShape<"workspace">;

export const workspaceShapeProps = {
  w: T.number,
  h: T.number,
  workspaceId: T.string,
  userId: T.string,
  userName: T.string,
  pageSlug: T.string,
};

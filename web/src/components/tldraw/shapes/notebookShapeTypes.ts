import { T, type TLShape } from "tldraw";

export interface NotebookShapeProps {
  w: number;
  h: number;
  pageSlug: string;
}

// tldraw 5 custom-shape typing: augmenting this map teaches every editor
// API (createShapes, getShape, ...) about the shape type.
declare module "@tldraw/tlschema" {
  interface TLGlobalShapePropsMap {
    "notebook-panel": NotebookShapeProps;
  }
}

export type NotebookShape = TLShape<"notebook-panel">;

export const notebookShapeProps = {
  w: T.number,
  h: T.number,
  pageSlug: T.string,
};

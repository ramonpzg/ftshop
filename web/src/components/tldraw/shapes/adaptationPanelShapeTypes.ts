import { T, type TLShape } from "tldraw";

export interface AdaptationPanelShapeProps {
  w: number;
  h: number;
  pageSlug: string;
}

// tldraw 5 custom-shape typing: augmenting this map teaches every editor
// API (createShapes, getShape, ...) about the shape type.
declare module "@tldraw/tlschema" {
  interface TLGlobalShapePropsMap {
    "adaptation-panel": AdaptationPanelShapeProps;
  }
}

export type AdaptationPanelShape = TLShape<"adaptation-panel">;

export const adaptationPanelShapeProps = {
  w: T.number,
  h: T.number,
  pageSlug: T.string,
};

import { T, type TLShape } from "tldraw";

export interface ModalityPanelShapeProps {
  w: number;
  h: number;
  modality: string;
  pageSlug: string;
}

// tldraw 5 custom-shape typing: augmenting this map teaches every editor
// API (createShapes, getShape, ...) about the shape type.
declare module "@tldraw/tlschema" {
  interface TLGlobalShapePropsMap {
    "modality-panel": ModalityPanelShapeProps;
  }
}

export type ModalityPanelShape = TLShape<"modality-panel">;

export const modalityPanelShapeProps = {
  w: T.number,
  h: T.number,
  modality: T.string,
  pageSlug: T.string,
};

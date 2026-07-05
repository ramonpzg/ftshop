import { T, type TLBaseShape } from "tldraw";

export type ModalityPanelShape = TLBaseShape<
  "modality-panel",
  {
    w: number;
    h: number;
    modality: string;
    pageSlug: string;
  }
>;

export const modalityPanelShapeProps = {
  w: T.number,
  h: T.number,
  modality: T.string,
  pageSlug: T.string,
};

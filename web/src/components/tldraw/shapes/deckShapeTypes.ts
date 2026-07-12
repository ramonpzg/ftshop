import { T, type TLShape } from "tldraw";

export interface DeckShapeProps {
  w: number;
  h: number;
  url: string;
}

declare module "@tldraw/tlschema" {
  interface TLGlobalShapePropsMap {
    "deck-panel": DeckShapeProps;
  }
}

export type DeckShape = TLShape<"deck-panel">;

export const deckShapeProps = {
  w: T.number,
  h: T.number,
  url: T.string,
};

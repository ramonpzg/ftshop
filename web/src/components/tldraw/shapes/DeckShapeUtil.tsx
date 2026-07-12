import { BaseBoxShapeUtil, HTMLContainer, useIsEditing } from "tldraw";
import { DeckPanel } from "../../deck/DeckPanel";
import { type DeckShape, deckShapeProps } from "./deckShapeTypes";

export class DeckShapeUtil extends BaseBoxShapeUtil<DeckShape> {
  static override type = "deck-panel" as const;
  static override props = deckShapeProps;

  override canEdit() {
    return true;
  }

  // Wheel events inside an opened deck go to the slides, not the canvas.
  override canScroll() {
    return true;
  }

  override isAspectRatioLocked() {
    return false;
  }

  getDefaultProps(): DeckShape["props"] {
    return { w: 1440, h: 850, url: "http://localhost:3030" };
  }

  component(shape: DeckShape) {
    // biome-ignore lint/correctness/useHookAtTopLevel: tldraw renders this method as a React component
    const isEditing = useIsEditing(shape.id);
    return (
      <HTMLContainer
        style={{ pointerEvents: isEditing ? "all" : "none", overflow: "hidden" }}
        onPointerDown={isEditing ? (event) => this.editor.markEventAsHandled(event) : undefined}
      >
        <DeckPanel defaultUrl={shape.props.url} isEditing={isEditing} />
      </HTMLContainer>
    );
  }

  override getIndicatorPath(shape: DeckShape): Path2D {
    const path = new Path2D();
    path.roundRect(0, 0, shape.props.w, shape.props.h, 8);
    return path;
  }
}

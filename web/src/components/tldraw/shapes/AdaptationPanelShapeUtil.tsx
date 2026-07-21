import { BaseBoxShapeUtil, HTMLContainer, useIsEditing } from "tldraw";
import { AdaptationPanel } from "../../adaptation/AdaptationPanel";
import { type AdaptationPanelShape, adaptationPanelShapeProps } from "./adaptationPanelShapeTypes";

export class AdaptationPanelShapeUtil extends BaseBoxShapeUtil<AdaptationPanelShape> {
  static override type = "adaptation-panel" as const;
  static override props = adaptationPanelShapeProps;

  override canEdit() {
    return true;
  }

  // Wheel events inside an opened panel scroll its content instead of
  // zooming the canvas.
  override canScroll() {
    return true;
  }

  override isAspectRatioLocked() {
    return false;
  }

  getDefaultProps(): AdaptationPanelShape["props"] {
    return { w: 1400, h: 1040, pageSlug: "" };
  }

  component(shape: AdaptationPanelShape) {
    // biome-ignore lint/correctness/useHookAtTopLevel: tldraw renders this method as a React component
    const isEditing = useIsEditing(shape.id);
    return (
      <HTMLContainer
        style={{ pointerEvents: isEditing ? "all" : "none", overflow: "hidden" }}
        onPointerDown={isEditing ? (event) => this.editor.markEventAsHandled(event) : undefined}
      >
        <AdaptationPanel isEditing={isEditing} />
      </HTMLContainer>
    );
  }

  override getIndicatorPath(shape: AdaptationPanelShape): Path2D {
    const path = new Path2D();
    path.roundRect(0, 0, shape.props.w, shape.props.h, 8);
    return path;
  }
}

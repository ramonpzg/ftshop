import { BaseBoxShapeUtil, HTMLContainer, useIsEditing } from "tldraw";
import { ModalityPanel } from "../../modality/ModalityPanel";
import { type ModalityPanelShape, modalityPanelShapeProps } from "./modalityPanelShapeTypes";

export class ModalityPanelShapeUtil extends BaseBoxShapeUtil<ModalityPanelShape> {
  static override type = "modality-panel" as const;
  static override props = modalityPanelShapeProps;

  override canEdit() {
    return true;
  }

  override isAspectRatioLocked() {
    return false;
  }

  getDefaultProps(): ModalityPanelShape["props"] {
    return { w: 900, h: 420, modality: "", pageSlug: "" };
  }

  component(shape: ModalityPanelShape) {
    // biome-ignore lint/correctness/useHookAtTopLevel: tldraw renders this method as a React component
    const isEditing = useIsEditing(shape.id);
    return (
      <HTMLContainer
        style={{ pointerEvents: isEditing ? "all" : "none", overflow: "hidden" }}
        onPointerDown={isEditing ? (event) => this.editor.markEventAsHandled(event) : undefined}
      >
        <ModalityPanel modality={shape.props.modality} isEditing={isEditing} />
      </HTMLContainer>
    );
  }

  override getIndicatorPath(shape: ModalityPanelShape): Path2D {
    const path = new Path2D();
    path.roundRect(0, 0, shape.props.w, shape.props.h, 8);
    return path;
  }
}

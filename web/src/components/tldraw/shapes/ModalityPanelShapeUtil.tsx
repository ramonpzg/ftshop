import { BaseBoxShapeUtil, HTMLContainer, stopEventPropagation, useIsEditing } from "tldraw";
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
    const isEditing = useIsEditing(shape.id);
    return (
      <HTMLContainer
        style={{ pointerEvents: isEditing ? "all" : "none", overflow: "hidden" }}
        onPointerDown={isEditing ? stopEventPropagation : undefined}
      >
        <ModalityPanel modality={shape.props.modality} isEditing={isEditing} />
      </HTMLContainer>
    );
  }

  indicator(shape: ModalityPanelShape) {
    return <rect width={shape.props.w} height={shape.props.h} rx={8} />;
  }
}

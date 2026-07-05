import { BaseBoxShapeUtil, HTMLContainer, stopEventPropagation, useIsEditing } from "tldraw";
import { WorkspacePanel } from "../../workspace/WorkspacePanel";
import { type WorkspaceShape, workspaceShapeProps } from "./workspaceShapeTypes";

export class WorkspaceShapeUtil extends BaseBoxShapeUtil<WorkspaceShape> {
  static override type = "workspace" as const;
  static override props = workspaceShapeProps;

  override canEdit() {
    return true;
  }

  override isAspectRatioLocked() {
    return false;
  }

  getDefaultProps(): WorkspaceShape["props"] {
    return {
      w: 900,
      h: 560,
      workspaceId: "",
      userId: "",
      userName: "",
      pageSlug: "",
    };
  }

  component(shape: WorkspaceShape) {
    const isEditing = useIsEditing(shape.id);
    return (
      <HTMLContainer
        style={{ pointerEvents: isEditing ? "all" : "none", overflow: "hidden" }}
        onPointerDown={isEditing ? stopEventPropagation : undefined}
      >
        <WorkspacePanel shape={shape} isEditing={isEditing} />
      </HTMLContainer>
    );
  }

  indicator(shape: WorkspaceShape) {
    return <rect width={shape.props.w} height={shape.props.h} rx={8} />;
  }
}

import { BaseBoxShapeUtil, HTMLContainer, useIsEditing } from "tldraw";
import { WorkspacePanel } from "../../workspace/WorkspacePanel";
import { type WorkspaceShape, workspaceShapeProps } from "./workspaceShapeTypes";

export class WorkspaceShapeUtil extends BaseBoxShapeUtil<WorkspaceShape> {
  static override type = "workspace" as const;
  static override props = workspaceShapeProps;

  override canEdit() {
    return true;
  }

  // Wheel events inside an opened workspace scroll its dataset list and
  // code editor instead of zooming the canvas.
  override canScroll() {
    return true;
  }

  override isAspectRatioLocked() {
    return false;
  }

  getDefaultProps(): WorkspaceShape["props"] {
    return {
      w: 1240,
      h: 900,
      workspaceId: "",
      userId: "",
      userName: "",
      pageSlug: "",
    };
  }

  component(shape: WorkspaceShape) {
    // biome-ignore lint/correctness/useHookAtTopLevel: tldraw renders this method as a React component
    const isEditing = useIsEditing(shape.id);
    return (
      <HTMLContainer
        style={{ pointerEvents: isEditing ? "all" : "none", overflow: "hidden" }}
        onPointerDown={isEditing ? (event) => this.editor.markEventAsHandled(event) : undefined}
      >
        <WorkspacePanel shape={shape} isEditing={isEditing} />
      </HTMLContainer>
    );
  }

  override getIndicatorPath(shape: WorkspaceShape): Path2D {
    const path = new Path2D();
    path.roundRect(0, 0, shape.props.w, shape.props.h, 8);
    return path;
  }
}

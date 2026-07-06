import { BaseBoxShapeUtil, HTMLContainer, useIsEditing } from "tldraw";
import { NotebookPanel } from "../../notebook/NotebookPanel";
import { type NotebookShape, notebookShapeProps } from "./notebookShapeTypes";

export class NotebookShapeUtil extends BaseBoxShapeUtil<NotebookShape> {
  static override type = "notebook-panel" as const;
  static override props = notebookShapeProps;

  override canEdit() {
    return true;
  }

  // Wheel events inside an opened notebook scroll the notebook instead of
  // zooming the canvas.
  override canScroll() {
    return true;
  }

  override isAspectRatioLocked() {
    return false;
  }

  getDefaultProps(): NotebookShape["props"] {
    return { w: 1200, h: 650, pageSlug: "" };
  }

  component(shape: NotebookShape) {
    // biome-ignore lint/correctness/useHookAtTopLevel: tldraw renders this method as a React component
    const isEditing = useIsEditing(shape.id);
    return (
      <HTMLContainer
        style={{ pointerEvents: isEditing ? "all" : "none", overflow: "hidden" }}
        onPointerDown={isEditing ? (event) => this.editor.markEventAsHandled(event) : undefined}
      >
        <NotebookPanel pageSlug={shape.props.pageSlug} isEditing={isEditing} />
      </HTMLContainer>
    );
  }

  override getIndicatorPath(shape: NotebookShape): Path2D {
    const path = new Path2D();
    path.roundRect(0, 0, shape.props.w, shape.props.h, 8);
    return path;
  }
}

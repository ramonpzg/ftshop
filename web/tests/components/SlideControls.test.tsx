import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { SlideControls } from "../../src/components/tldraw/SlideControls";

function frameShape(id: string, name: string, x: number) {
  return { id, type: "frame", x, y: 0, props: { name } };
}

function makeEditor(shapes: ReturnType<typeof frameShape>[]) {
  return {
    getCurrentPageId: mock(() => "page:presentation"),
    getCurrentPageShapes: mock(() => shapes),
    getShapePageBounds: mock(() => ({ x: 0, y: 0, w: 1600, h: 900 })),
    zoomToBounds: mock(() => {}),
    getEditingShapeId: mock(() => null),
    getSelectedShapeIds: mock((): string[] => []),
  };
}

afterEach(cleanup);

describe("SlideControls", () => {
  test("renders nothing without an editor", () => {
    render(<SlideControls editor={null} />);
    expect(screen.queryByTestId("slide-controls")).toBeNull();
  });

  test("renders nothing on a page without frames", () => {
    const editor = makeEditor([{ id: "shape:n1", type: "note", x: 0, y: 0, props: { name: "" } }]);
    render(<SlideControls editor={editor as never} />);
    expect(screen.queryByTestId("slide-controls")).toBeNull();
  });

  test("shows the slide count and steps through the deck", () => {
    const editor = makeEditor([
      frameShape("shape:s2", "Slide 02", 1800),
      frameShape("shape:s1", "Slide 01", 0),
    ]);
    render(<SlideControls editor={editor as never} />);
    expect(screen.getByTestId("slide-controls-label").textContent).toBe("2 slides");

    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByTestId("slide-controls-label").textContent).toBe("1 / 2");
    expect(editor.zoomToBounds).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByTestId("slide-controls-label").textContent).toBe("2 / 2");

    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByTestId("slide-controls-label").textContent).toBe("2 / 2");

    fireEvent.click(screen.getByText("Prev"));
    expect(screen.getByTestId("slide-controls-label").textContent).toBe("1 / 2");
  });

  test("PageDown advances the deck from the keyboard", () => {
    const editor = makeEditor([frameShape("shape:s1", "Slide 01", 0)]);
    render(<SlideControls editor={editor as never} />);
    fireEvent.keyDown(window, { key: "PageDown" });
    expect(screen.getByTestId("slide-controls-label").textContent).toBe("1 / 1");
    expect(editor.zoomToBounds).toHaveBeenCalledTimes(1);
  });

  test("arrow keys are ignored while shapes are selected", () => {
    const editor = makeEditor([frameShape("shape:s1", "Slide 01", 0)]);
    editor.getSelectedShapeIds = mock(() => ["shape:x"]);
    render(<SlideControls editor={editor as never} />);
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(editor.zoomToBounds).not.toHaveBeenCalled();
  });

  test("keys are ignored while editing a shape", () => {
    const editor = makeEditor([frameShape("shape:s1", "Slide 01", 0)]);
    editor.getEditingShapeId = mock(() => "shape:x" as never);
    render(<SlideControls editor={editor as never} />);
    fireEvent.keyDown(window, { key: "PageDown" });
    expect(editor.zoomToBounds).not.toHaveBeenCalled();
  });
});

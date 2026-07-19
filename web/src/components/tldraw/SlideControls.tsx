import { CaretLeft, CaretRight } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Editor, TLShapeId } from "tldraw";
import { track } from "tldraw";
import { broadcastSlideTarget } from "../../actions/presenterNavigation";
import { orderSlides, type SlideFrame, stepSlideIndex } from "../../calculations/slides";
import { usePresenterState } from "../../lib/presenterContext";
import "./SlideControls.css";

interface SlideControlsProps {
  editor: Editor | null;
}

function getSlides(editor: Editor): SlideFrame[] {
  const frames = editor
    .getCurrentPageShapes()
    .filter((shape) => shape.type === "frame")
    .map((shape) => ({
      id: shape.id as string,
      name: (shape.props as { name?: string }).name ?? "",
      x: shape.x,
      y: shape.y,
    }));
  return orderSlides(frames);
}

function isTypingTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || target.closest("input, textarea, [contenteditable=true]") !== null)
  );
}

/**
 * Prev / Next navigation over the frames of the current page, in slide
 * order. Renders nothing on pages without frames. PageUp / PageDown always
 * step (that is what presenter clickers send); arrow keys step only when
 * nothing is selected, since tldraw uses them to nudge shapes.
 */
export const SlideControls = track(function SlideControls({ editor }: SlideControlsProps) {
  const { isPresenter, presenterMode } = usePresenterState();
  const indexRef = useRef(-1);
  const [index, setIndexState] = useState(-1);
  const pageId = editor?.getCurrentPageId();

  const setIndex = useCallback((value: number) => {
    indexRef.current = value;
    setIndexState(value);
  }, []);

  // biome-ignore lint/correctness/useExhaustiveDependencies: pageId is a reset trigger, not read in the body
  useEffect(() => {
    setIndex(-1);
  }, [pageId, setIndex]);

  const step = useCallback(
    (delta: -1 | 1) => {
      if (!editor) return;
      const slides = getSlides(editor);
      const next = stepSlideIndex(indexRef.current, slides.length, delta);
      if (next < 0 || next >= slides.length) return;
      const bounds = editor.getShapePageBounds(slides[next].id as TLShapeId);
      if (!bounds) return;
      setIndex(next);
      editor.zoomToBounds(bounds, { inset: 48, animation: { duration: 250 } });
      // While the room is in presenter mode, stepping also moves the
      // shared target, so attendees follow Prev/Next.
      if (isPresenter && presenterMode === "presenter") {
        broadcastSlideTarget(editor, slides[next].id).catch(() => {});
      }
    },
    [editor, setIndex, isPresenter, presenterMode],
  );

  useEffect(() => {
    if (!editor) return;
    function onKeyDown(event: KeyboardEvent) {
      if (!editor) return;
      const forward = event.key === "PageDown" || event.key === "ArrowRight";
      const backward = event.key === "PageUp" || event.key === "ArrowLeft";
      if (!forward && !backward) return;
      if (isTypingTarget(event.target)) return;
      if (editor.getEditingShapeId() !== null) return;
      const isArrow = event.key === "ArrowRight" || event.key === "ArrowLeft";
      if (isArrow && editor.getSelectedShapeIds().length > 0) return;
      if (getSlides(editor).length === 0) return;
      event.preventDefault();
      step(forward ? 1 : -1);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editor, step]);

  if (!editor) return null;
  const slides = getSlides(editor);
  if (slides.length === 0) return null;

  return (
    <div className="slide-controls" data-testid="slide-controls">
      <button type="button" onClick={() => step(-1)}>
        <CaretLeft size={12} weight="bold" />
        Prev
      </button>
      <span className="slide-controls-label" data-testid="slide-controls-label">
        {index >= 0 ? `${index + 1} / ${slides.length}` : `${slides.length} slides`}
      </span>
      <button type="button" onClick={() => step(1)}>
        Next
        <CaretRight size={12} weight="bold" />
      </button>
    </div>
  );
});

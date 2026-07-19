import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render, screen } from "@testing-library/react";
import { NotebookPanel } from "../../src/components/notebook/NotebookPanel";

afterEach(() => {
  cleanup();
});

describe("NotebookPanel", () => {
  test("points legacy canvas shapes to the standalone Jupyter notebook", () => {
    const { container } = render(<NotebookPanel pageSlug="text" isEditing={false} />);

    expect(screen.getByText("The notebook runs separately.")).toBeTruthy();
    expect(screen.getByText("just session-notebook")).toBeTruthy();
    expect(screen.getByText("Legacy canvas shape")).toBeTruthy();
    expect(container.querySelector("iframe")).toBeNull();
  });
});

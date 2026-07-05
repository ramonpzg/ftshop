import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MiniIde } from "../../src/components/ide/MiniIde";
import { SNIPPETS } from "../../src/lib/snippets";

afterEach(() => {
  cleanup();
});

describe("MiniIde", () => {
  test("renders a tab for every snippet", () => {
    render(<MiniIde selectedSnippetId={null} onSelectSnippet={() => {}} />);
    for (const snippet of SNIPPETS) {
      expect(screen.getByTestId(`snippet-tab-${snippet.id}`)).toBeTruthy();
    }
  });

  test("defaults to the first snippet when none is selected", () => {
    render(<MiniIde selectedSnippetId={null} onSelectSnippet={() => {}} />);
    const firstTab = screen.getByTestId(`snippet-tab-${SNIPPETS[0].id}`);
    expect(firstTab.className).toContain("mini-ide-tab-active");
  });

  test("marks the selected snippet's tab as active", () => {
    render(<MiniIde selectedSnippetId="reward_function" onSelectSnippet={() => {}} />);
    expect(screen.getByTestId("snippet-tab-reward_function").className).toContain(
      "mini-ide-tab-active",
    );
    expect(screen.getByTestId("snippet-tab-prompt_template").className).not.toContain(
      "mini-ide-tab-active",
    );
  });

  test("clicking a tab calls onSelectSnippet with its id", () => {
    const onSelectSnippet = mock((_id: string) => {});
    render(<MiniIde selectedSnippetId="prompt_template" onSelectSnippet={onSelectSnippet} />);

    fireEvent.click(screen.getByTestId("snippet-tab-reward_function"));

    expect(onSelectSnippet).toHaveBeenCalledWith("reward_function");
  });
});

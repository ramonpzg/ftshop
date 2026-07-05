import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ChessBoard } from "../../src/components/chess/ChessBoard";

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

afterEach(() => {
  cleanup();
});

describe("ChessBoard", () => {
  test("renders 64 squares", () => {
    render(<ChessBoard fen={STARTING_FEN} interactive={false} onMove={() => {}} />);
    expect(screen.getAllByTestId(/^square-/).length).toBe(64);
  });

  test("squares are disabled when not interactive", () => {
    render(<ChessBoard fen={STARTING_FEN} interactive={false} onMove={() => {}} />);
    expect(screen.getByTestId("square-e2").hasAttribute("disabled")).toBe(true);
  });

  test("selecting a piece then a destination calls onMove with the uci", () => {
    const onMove = mock((_uci: string) => {});
    render(<ChessBoard fen={STARTING_FEN} interactive={true} onMove={onMove} />);

    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e4"));

    expect(onMove).toHaveBeenCalledTimes(1);
    expect(onMove.mock.calls[0][0]).toBe("e2e4");
  });

  test("clicking an empty square first does not select anything", () => {
    const onMove = mock((_uci: string) => {});
    render(<ChessBoard fen={STARTING_FEN} interactive={true} onMove={onMove} />);

    fireEvent.click(screen.getByTestId("square-e4"));
    fireEvent.click(screen.getByTestId("square-e5"));

    expect(onMove).not.toHaveBeenCalled();
  });

  test("clicking the same square twice deselects it", () => {
    const onMove = mock((_uci: string) => {});
    render(<ChessBoard fen={STARTING_FEN} interactive={true} onMove={onMove} />);

    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e4"));

    expect(onMove).not.toHaveBeenCalled();
  });
});

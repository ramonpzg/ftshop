import { describe, expect, test } from "bun:test";
import {
  buildUciMove,
  isLightSquare,
  parseFenBoard,
  pieceAssetPath,
  squareName,
} from "../../src/calculations/chessBoard";

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

describe("parseFenBoard", () => {
  test("parses 8 rows of 8 squares", () => {
    const board = parseFenBoard(STARTING_FEN);
    expect(board.length).toBe(8);
    for (const row of board) expect(row.length).toBe(8);
  });

  test("places black pieces on the first row (rank 8)", () => {
    const board = parseFenBoard(STARTING_FEN);
    expect(board[0]).toEqual(["r", "n", "b", "q", "k", "b", "n", "r"]);
  });

  test("places white pawns on rank 2", () => {
    const board = parseFenBoard(STARTING_FEN);
    expect(board[6]).toEqual(["P", "P", "P", "P", "P", "P", "P", "P"]);
  });

  test("parses empty ranks as all-null", () => {
    const board = parseFenBoard(STARTING_FEN);
    expect(board[3].every((cell) => cell === null)).toBe(true);
  });

  test("ignores the rest of the FEN string", () => {
    const board = parseFenBoard(`${STARTING_FEN} extra fields ignored`);
    expect(board[0][4]).toBe("k");
  });
});

describe("squareName", () => {
  test("row 0 col 0 is a8", () => {
    expect(squareName(0, 0)).toBe("a8");
  });

  test("row 7 col 7 is h1", () => {
    expect(squareName(7, 7)).toBe("h1");
  });

  test("row 6 col 4 is e2", () => {
    expect(squareName(6, 4)).toBe("e2");
  });
});

describe("isLightSquare", () => {
  test("a8 (row 0, col 0) is light by this convention", () => {
    expect(isLightSquare(0, 0)).toBe(true);
  });

  test("alternates across a row", () => {
    expect(isLightSquare(0, 1)).toBe(false);
  });
});

describe("pieceAssetPath", () => {
  test("uppercase letters are white", () => {
    expect(pieceAssetPath("K")).toBe("/pieces/wK.svg");
  });

  test("lowercase letters are black", () => {
    expect(pieceAssetPath("q")).toBe("/pieces/bQ.svg");
  });
});

describe("buildUciMove", () => {
  const board = parseFenBoard(STARTING_FEN);

  test("builds a plain move for non-promoting pieces", () => {
    expect(buildUciMove("e2", "e4", board)).toBe("e2e4");
  });

  test("auto-promotes a pawn reaching the 8th rank", () => {
    const boardWithPawnOnSeventh = parseFenBoard("8/4P3/8/8/8/8/8/4K2k w - - 0 1");
    expect(buildUciMove("e7", "e8", boardWithPawnOnSeventh)).toBe("e7e8q");
  });

  test("auto-promotes a black pawn reaching the 1st rank", () => {
    const boardWithPawnOnSecond = parseFenBoard("4k2K/8/8/8/8/8/4p3/8 b - - 0 1");
    expect(buildUciMove("e2", "e1", boardWithPawnOnSecond)).toBe("e2e1q");
  });

  test("does not promote a non-pawn reaching the back rank", () => {
    const boardWithRookOnSeventh = parseFenBoard("8/4R3/8/8/8/8/8/4K2k w - - 0 1");
    expect(buildUciMove("e7", "e8", boardWithRookOnSeventh)).toBe("e7e8");
  });
});

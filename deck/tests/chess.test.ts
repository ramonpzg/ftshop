import { describe, expect, test } from "bun:test";
import { boardFromFen, NOTATION_EXAMPLE, START_FEN } from "../lib/chess";

describe("boardFromFen", () => {
  test("expands the start position into 64 squares, rank 8 first", () => {
    const board = boardFromFen(START_FEN);
    expect(board).toHaveLength(64);
    expect(board[0].square).toBe("a8");
    expect(board[63].square).toBe("h1");
  });

  test("places the right glyphs on the right squares", () => {
    const board = boardFromFen(START_FEN);
    const at = (square: string) => board.find((cell) => cell.square === square);
    expect(at("e1")?.glyph).toBe("♔");
    expect(at("d8")?.glyph).toBe("♛");
    expect(at("a2")?.glyph).toBe("♙");
    expect(at("e4")?.glyph).toBeNull();
  });

  test("checkerboard coloring matches the board: a1 dark, h1 light", () => {
    const board = boardFromFen(START_FEN);
    const at = (square: string) => board.find((cell) => cell.square === square);
    expect(at("a1")?.light).toBe(false);
    expect(at("h1")?.light).toBe(true);
    expect(at("a8")?.light).toBe(true);
  });

  test("the notation example position has the bishop still on f1", () => {
    const board = boardFromFen(NOTATION_EXAMPLE.positionFen);
    const at = (square: string) => board.find((cell) => cell.square === square);
    expect(at("f1")?.glyph).toBe("♗");
    expect(at("b5")?.glyph).toBeNull();
    expect(at("c6")?.glyph).toBe("♞");
    expect(at("f3")?.glyph).toBe("♘");
  });

  test("rejects malformed placements instead of rendering nonsense", () => {
    expect(() => boardFromFen("rnbqkbnr/pppppppp/8/8")).toThrow();
    expect(() => boardFromFen("rnbqkbnr/ppppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w")).toThrow();
    expect(() => boardFromFen("xnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w")).toThrow();
  });
});

describe("NOTATION_EXAMPLE", () => {
  test("uses the same actual move in every representation", () => {
    const [fen, uci, san, pgn] = NOTATION_EXAMPLE.representations;
    expect(fen.value).toBe(NOTATION_EXAMPLE.positionFen);
    expect(uci.value).toBe(`${NOTATION_EXAMPLE.from}${NOTATION_EXAMPLE.to}`);
    expect(san.value).toBe("Bb5");
    expect(pgn.value.endsWith("Bb5")).toBe(true);
  });
});

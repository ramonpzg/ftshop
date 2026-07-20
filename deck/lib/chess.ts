/** Chess data for the deck's board renderer and notation slides.
 *
 * Pure calculations only. The board component renders whatever these
 * functions return; tests exercise them directly.
 */

export interface BoardSquare {
  /** Algebraic name, a1 through h8. */
  square: string;
  /** Unicode piece glyph, or null for an empty square. */
  glyph: string | null;
  /** Light square in the checkerboard sense. */
  light: boolean;
}

const GLYPHS: Record<string, string> = {
  K: "♔",
  Q: "♕",
  R: "♖",
  B: "♗",
  N: "♘",
  P: "♙",
  k: "♚",
  q: "♛",
  r: "♜",
  b: "♝",
  n: "♞",
  p: "♟",
};

const FILES = "abcdefgh";

/** Expand the piece-placement field of a FEN into 64 squares in
 * display order: rank 8 first, files a to h. Throws on a malformed
 * placement so a typo fails a test instead of rendering nonsense. */
export function boardFromFen(fen: string): BoardSquare[] {
  const placement = fen.split(" ")[0];
  const ranks = placement.split("/");
  if (ranks.length !== 8) throw new Error(`FEN needs 8 ranks: ${fen}`);
  const squares: BoardSquare[] = [];
  ranks.forEach((rank, rankIndex) => {
    const rankNumber = 8 - rankIndex;
    let file = 0;
    for (const ch of rank) {
      if (/[1-8]/.test(ch)) {
        for (let i = 0; i < Number(ch); i += 1) {
          squares.push(makeSquare(file, rankNumber, null));
          file += 1;
        }
      } else if (GLYPHS[ch]) {
        squares.push(makeSquare(file, rankNumber, GLYPHS[ch]));
        file += 1;
      } else {
        throw new Error(`Bad FEN character '${ch}' in ${fen}`);
      }
    }
    if (file !== 8) throw new Error(`Rank ${rankNumber} has ${file} files: ${fen}`);
  });
  return squares;
}

function makeSquare(file: number, rankNumber: number, glyph: string | null): BoardSquare {
  return {
    square: `${FILES[file]}${rankNumber}`,
    glyph,
    light: (file + rankNumber) % 2 === 0,
  };
}

/** The one move the notation slide uses in every representation:
 * 3. Bb5 in the Ruy Lopez. Same actual move everywhere, per PLAN_V2. */
export const NOTATION_EXAMPLE = {
  positionFen: "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
  positionLabel: "After 2...Nc6. White to move.",
  from: "f1",
  to: "b5",
  representations: [
    {
      name: "FEN",
      stores: "the position",
      value: "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
      point: "One line stores the whole board state. This is what the model is shown.",
    },
    {
      name: "UCI",
      stores: "a move, for machines",
      value: "f1b5",
      point: "From-square, to-square. No context needed to apply it.",
    },
    {
      name: "SAN",
      stores: "a move, for people",
      value: "Bb5",
      point: "Piece and destination. This is how a game reads in a book.",
    },
    {
      name: "PGN",
      stores: "the game history",
      value: "1. e4 e5 2. Nf3 Nc6 3. Bb5",
      point: "The whole game as text. Datasets slice prefixes out of this.",
    },
  ],
} as const;

/** Start position for the rules recap board. */
export const START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

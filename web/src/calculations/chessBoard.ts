/** Pure FEN parsing and square/piece math for the SVG chess board. No I/O. */

export type PieceCode = "P" | "N" | "B" | "R" | "Q" | "K" | "p" | "n" | "b" | "r" | "q" | "k";

/** 8 rows (rank 8 first, matching FEN order) x 8 columns (file a first). */
export type BoardGrid = (PieceCode | null)[][];

export function parseFenBoard(fen: string): BoardGrid {
  const placement = fen.split(" ")[0];
  return placement.split("/").map((row) => {
    const cells: (PieceCode | null)[] = [];
    for (const char of row) {
      if (/[1-8]/.test(char)) {
        for (let i = 0; i < Number(char); i++) cells.push(null);
      } else {
        cells.push(char as PieceCode);
      }
    }
    return cells;
  });
}

export function squareName(row: number, col: number): string {
  const file = String.fromCharCode("a".charCodeAt(0) + col);
  const rank = 8 - row;
  return `${file}${rank}`;
}

export function isLightSquare(row: number, col: number): boolean {
  return (row + col) % 2 === 0;
}

export function pieceAssetPath(piece: PieceCode): string {
  const color = piece === piece.toUpperCase() ? "w" : "b";
  const type = piece.toUpperCase();
  return `/pieces/${color}${type}.svg`;
}

/** Builds a UCI move string, auto-promoting pawns reaching the back rank to queen. */
export function buildUciMove(from: string, to: string, board: BoardGrid): string {
  const piece = pieceAtSquare(board, from);
  const isPawn = piece?.toUpperCase() === "P";
  const targetRank = to[1];
  const promotes = isPawn && (targetRank === "8" || targetRank === "1");
  return promotes ? `${from}${to}q` : `${from}${to}`;
}

export function pieceAtSquare(board: BoardGrid, square: string): PieceCode | null {
  const col = square.charCodeAt(0) - "a".charCodeAt(0);
  const row = 8 - Number(square[1]);
  return board[row]?.[col] ?? null;
}

export function isSameColor(a: PieceCode, b: PieceCode): boolean {
  const aWhite = a === a.toUpperCase();
  const bWhite = b === b.toUpperCase();
  return aWhite === bWhite;
}

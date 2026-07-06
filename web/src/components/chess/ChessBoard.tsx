import { useState } from "react";
import {
  buildUciMove,
  isLightSquare,
  isSameColor,
  parseFenBoard,
  pieceAssetPath,
  pieceAtSquare,
  squareName,
} from "../../calculations/chessBoard";
import "./ChessBoard.css";

interface ChessBoardProps {
  fen: string;
  interactive: boolean;
  onMove: (uci: string) => void;
}

export function ChessBoard({ fen, interactive, onMove }: ChessBoardProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const board = parseFenBoard(fen);

  function handleSquareClick(square: string) {
    if (!interactive) return;
    const piece = pieceAtSquare(board, square);

    if (!selected) {
      if (piece) setSelected(square);
      return;
    }
    if (selected === square) {
      setSelected(null);
      return;
    }
    // Clicking another of your own pieces re-selects it rather than
    // firing a capture-your-own-piece request the server would reject.
    const selectedPiece = pieceAtSquare(board, selected);
    if (piece && selectedPiece && isSameColor(piece, selectedPiece)) {
      setSelected(square);
      return;
    }
    onMove(buildUciMove(selected, square, board));
    setSelected(null);
  }

  return (
    <div className="chess-board" data-testid="chess-board">
      {board.map((row, rowIndex) =>
        row.map((piece, colIndex) => {
          const square = squareName(rowIndex, colIndex);
          return (
            <button
              key={square}
              type="button"
              className={[
                "chess-square",
                isLightSquare(rowIndex, colIndex) ? "chess-square-light" : "chess-square-dark",
                selected === square ? "chess-square-selected" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => handleSquareClick(square)}
              disabled={!interactive}
              data-testid={`square-${square}`}
              aria-label={square}
            >
              {piece && (
                <img src={pieceAssetPath(piece)} alt={piece} className="chess-piece-image" />
              )}
            </button>
          );
        }),
      )}
    </div>
  );
}

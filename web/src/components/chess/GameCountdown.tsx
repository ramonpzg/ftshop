import { Timer } from "@phosphor-icons/react";
import { memo, useEffect, useRef, useState } from "react";
import type { Game } from "../../data/api";
import { formatClock } from "../../lib/gameClock";

interface GameCountdownProps {
  game: Game;
  /** Called when the local clock hits zero. The parent asks the server
   * to confirm before recording anything; return false if the server
   * disagrees (clock skew) so the countdown keeps trying. */
  onExpired: () => Promise<boolean>;
}

/** The ticking clock, isolated on purpose: it re-renders itself twice a
 * second, and nothing else. Keeping this state in the workspace panel
 * re-rendered the whole tree (board, dataset, CodeMirror) on every tick,
 * which is what made the board feel sticky. */
export const GameCountdown = memo(function GameCountdown({ game, onExpired }: GameCountdownProps) {
  const [secondsLeft, setSecondsLeft] = useState(game.seconds_left);
  const expiredRef = useRef(false);

  // biome-ignore lint/correctness/useExhaustiveDependencies: keyed on the game id on purpose; status refetches must not restart the deadline
  useEffect(() => {
    const deadline = Date.now() + game.seconds_left * 1000;
    expiredRef.current = false;
    setSecondsLeft(game.seconds_left);
    const tick = setInterval(async () => {
      const left = (deadline - Date.now()) / 1000;
      setSecondsLeft(left);
      if (left <= 0 && !expiredRef.current) {
        expiredRef.current = true;
        const ended = await onExpired();
        if (!ended) expiredRef.current = false;
      }
    }, 500);
    return () => clearInterval(tick);
  }, [game.id]);

  return (
    <span className="workspace-game-timer" data-testid="game-timer">
      <Timer size={13} weight="bold" />
      {formatClock(secondsLeft)}
    </span>
  );
});

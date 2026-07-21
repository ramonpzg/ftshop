"""Simulates a room of attendees hammering a running backend.

Each simulated attendee does what the real UI does: joins, gets a
workspace, starts a timed match, plays legal moves with think time in
between, triggers the model's reply (retrying an open model turn the
way the UI's retry button does), and polls presenter state every three
seconds. One extra client polls the presenter dashboard. At the end it
prints per-endpoint latency percentiles, error counts (every non-2xx
response and every transport failure), the model-turn outcome tally,
and an explicit verdict on whether this run certifies ROOM_MODEL_PLAY.

Assessments are deliberately absent from the workload: since the room
model policy they are manual and presenter-only, one per beat, so
simulating one per exchange would double model traffic the real room
no longer produces.

    just start-backend            # terminal 1, pointed at just mock-llm
    just mock-llm                 # terminal 2
    just load-test 40 60          # terminal 3: 40 attendees, 60 seconds

Without an LLM configured on the backend the sim plays both sides
itself, which still exercises moves, dataset writes, and polling, just
not the thread-holding upstream calls. The verdict then says plainly
that the run measured the backend only.

The mock run proves the backend, not inference. The run that decides
whether the room may play the model is the same command with the
backend pointed at the real local endpoint (llama.cpp serving Gemma)
on the venue machine. ROOM_MODEL_PLAY=1 is set only on a PASS verdict:
model-move p95 inside the turn deadline, zero model-move errors, zero
unavailable or stale turns. Fallback moves do not fail the verdict;
they are the model answering badly, not the server failing to answer.
The sim connects from loopback, so it passes the room policy's
presenter-machine gates without any flags: it can always measure a
closed room. The verdict compares against this process's
MODEL_TURN_DEADLINE_SECONDS (override with --turn-deadline), so run it
from the same shell environment as the backend.
"""

import argparse
import asyncio
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass

import chess
import httpx

from euro_chess_studio.actions.model_turn import deadline_seconds

PRESENTER_POLL_SECONDS = 3.0
MODEL_MOVE_ENDPOINT = "POST model-move"
MODEL_TURN_OUTCOMES = ("model_move", "fallback_move", "unavailable", "stale")


def is_error_status(status: int) -> bool:
    """Every non-2xx counts, plus 0 for a transport failure. A 403 from
    a policy gate or a 409 from a turn conflict is the backend refusing
    work the room asked for; a capacity run that hides those would
    certify a room that cannot actually play."""
    return status == 0 or not 200 <= status < 300


def percentile(sorted_latencies: list[float], q: float) -> float:
    return sorted_latencies[min(len(sorted_latencies) - 1, int(q * len(sorted_latencies)))]


class Metrics:
    def __init__(self) -> None:
        self.samples: dict[str, list[tuple[float, int]]] = defaultdict(list)

    def add(self, endpoint: str, ms: float, status: int) -> None:
        self.samples[endpoint].append((ms, status))

    def report(self) -> str:
        lines = [
            f"{'endpoint':<28} {'n':>6} {'err':>5} {'p50':>7} {'p95':>7} {'p99':>7} {'max':>8}"
        ]
        for endpoint in sorted(self.samples):
            rows = self.samples[endpoint]
            latencies = sorted(ms for ms, _ in rows)
            errors = sum(1 for _, status in rows if is_error_status(status))
            lines.append(
                f"{endpoint:<28} {len(rows):>6} {errors:>5} "
                f"{percentile(latencies, 0.50):>6.0f}ms {percentile(latencies, 0.95):>6.0f}ms "
                f"{percentile(latencies, 0.99):>6.0f}ms {latencies[-1]:>7.0f}ms"
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class ModelTurnView:
    """What one 200 from /model-move means for the simulated attendee:
    the outcome, the new fen when a move actually landed (only
    model_move and fallback_move carry one; unavailable and stale leave
    the board unchanged with move null), and whether the game ended."""

    outcome: str
    next_fen: str | None
    game_over: bool


def interpret_model_turn(body: dict) -> ModelTurnView:
    """Pure. Crashing on move null was exactly how the simulator used
    to misread an overloaded room: the outcomes that signal overload
    were the ones it could not survive."""
    move = body.get("move")
    next_fen = None
    if move is not None and move.get("is_legal"):
        next_fen = move["fen_after"]
    return ModelTurnView(
        outcome=body.get("outcome", "unknown"),
        next_fen=next_fen,
        game_over=bool(body.get("game_result")),
    )


@dataclass(frozen=True)
class Verdict:
    """The run's answer to "may ROOM_MODEL_PLAY=1 be set?". passed is
    None when the run carried no model traffic and cannot answer."""

    passed: bool | None
    lines: tuple[str, ...]


def build_verdict(
    model_move_samples: list[tuple[float, int]],
    outcomes: dict[str, int],
    turn_deadline_seconds: float,
) -> Verdict:
    """Pure. PASS requires model-move p95 inside the turn deadline,
    zero model-move errors, and zero unavailable or stale turns.
    Fallback moves are reported but do not fail the verdict: a fallback
    is the model answering badly, not the server failing to answer."""
    tally = ", ".join(f"{outcomes.get(name, 0)} {name}" for name in MODEL_TURN_OUTCOMES)
    unknown = sum(count for name, count in outcomes.items() if name not in MODEL_TURN_OUTCOMES)
    if unknown:
        tally += f", {unknown} unknown"
    if not model_move_samples:
        return Verdict(
            passed=None,
            lines=(
                f"model turns: {tally}",
                "VERDICT: NO MODEL TRAFFIC. This run measured the backend only "
                "and cannot certify ROOM_MODEL_PLAY.",
            ),
        )
    latencies = sorted(ms for ms, _ in model_move_samples)
    p95_ms = percentile(latencies, 0.95)
    errors = sum(1 for _, status in model_move_samples if is_error_status(status))
    unavailable = outcomes.get("unavailable", 0)
    stale = outcomes.get("stale", 0)
    reasons = []
    if p95_ms > turn_deadline_seconds * 1000:
        reasons.append(
            f"model-move p95 {p95_ms:.0f}ms exceeds the {turn_deadline_seconds:.0f}s turn deadline"
        )
    if errors:
        reasons.append(f"{errors} model-move error(s)")
    if unavailable or stale:
        reasons.append(f"{unavailable} unavailable and {stale} stale model turn(s)")
    lines = [f"model turns: {tally}"]
    if reasons:
        lines.append(
            "VERDICT: FAIL. " + "; ".join(reasons) + ". Leave ROOM_MODEL_PLAY "
            "unset and run segment 5 in free-play mode."
        )
        return Verdict(passed=False, lines=tuple(lines))
    lines.append(
        f"VERDICT: PASS. model-move p95 {p95_ms:.0f}ms inside the "
        f"{turn_deadline_seconds:.0f}s turn deadline, no errors, no "
        "unavailable or stale turns. ROOM_MODEL_PLAY=1 may be set for "
        "this endpoint on this machine."
    )
    return Verdict(passed=True, lines=tuple(lines))


async def timed(
    metrics: Metrics,
    endpoint: str,
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response | None:
    start = time.perf_counter()
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.HTTPError:
        metrics.add(endpoint, (time.perf_counter() - start) * 1000, 0)
        return None
    metrics.add(endpoint, (time.perf_counter() - start) * 1000, response.status_code)
    return response


async def attendee(
    index: int,
    base: str,
    deadline: float,
    think: float,
    metrics: Metrics,
    outcomes: Counter,
    rng: random.Random,
) -> int:
    moves_played = 0
    async with httpx.AsyncClient(base_url=base, timeout=30.0) as client:
        user = await timed(
            metrics, "POST /users", client, "POST", "/users", json={"name": f"sim-{index}"}
        )
        if user is None or user.status_code != 201:
            return 0
        workspace = await timed(
            metrics,
            "POST /workspaces",
            client,
            "POST",
            "/workspaces",
            json={"user_id": user.json()["id"], "page_slug": "chess-machine"},
        )
        if workspace is None or workspace.status_code != 201:
            return 0
        wid = workspace.json()["id"]

        llm = await timed(metrics, "GET /llm/status", client, "GET", "/llm/status")
        llm_ready = llm is not None and llm.status_code == 200 and llm.json()["configured"]

        async def poll_presenter() -> None:
            while time.monotonic() < deadline:
                await timed(metrics, "GET /presenter", client, "GET", "/presenter")
                await asyncio.sleep(PRESENTER_POLL_SECONDS)

        poller = asyncio.create_task(poll_presenter())

        async def start_game() -> str | None:
            response = await timed(
                metrics,
                "POST game/start",
                client,
                "POST",
                f"/workspaces/{wid}/game/start",
                json={"time_limit_seconds": 300},
            )
            if response is None or response.status_code != 200:
                return None
            return response.json()["board_fen"]

        async def pause() -> None:
            await asyncio.sleep(rng.uniform(think * 0.5, think * 1.5))

        fen = await start_game()
        # Turn-aware: with a model configured, the sim plays white and
        # asks the model for black, retrying an open model turn (an
        # unavailable or stale outcome leaves black to move) the way
        # the UI's retry button does, instead of 409-spiraling the game
        # into a restart. Without a model it plays both sides.
        while time.monotonic() < deadline and fen is not None:
            board = chess.Board(fen)
            if not board.legal_moves:
                fen = await start_game()
                continue

            if llm_ready and board.turn == chess.BLACK:
                reply = await timed(
                    metrics,
                    MODEL_MOVE_ENDPOINT,
                    client,
                    "POST",
                    f"/workspaces/{wid}/model-move",
                )
                if reply is not None and reply.status_code == 200:
                    view = interpret_model_turn(reply.json())
                    outcomes[view.outcome] += 1
                    if view.next_fen is not None:
                        moves_played += 1
                        fen = view.next_fen
                    if view.game_over:
                        fen = await start_game()
                        continue
                # Non-200s are already in the metrics; the board is
                # unchanged either way, so the next iteration retries.
                await pause()
                continue

            uci = rng.choice([m.uci() for m in board.legal_moves]).lower()
            response = await timed(
                metrics, "POST moves", client, "POST", f"/workspaces/{wid}/moves", json={"uci": uci}
            )
            if response is None:
                break
            if response.status_code == 409:
                fen = await start_game()
                continue
            if response.status_code != 200:
                break
            body = response.json()
            moves_played += 1
            if body["move"]["is_legal"]:
                fen = body["move"]["fen_after"]
            if body["game_result"]:
                fen = await start_game()
                continue
            await pause()

        poller.cancel()
    return moves_played


async def presenter_dashboard(base: str, deadline: float, metrics: Metrics) -> None:
    async with httpx.AsyncClient(base_url=base, timeout=30.0) as client:
        while time.monotonic() < deadline:
            await timed(metrics, "GET presenter/games", client, "GET", "/presenter/games")
            await asyncio.sleep(PRESENTER_POLL_SECONDS)


async def run(args: argparse.Namespace) -> None:
    metrics = Metrics()
    outcomes: Counter = Counter()
    deadline = time.monotonic() + args.duration
    rng = random.Random(args.seed)
    attendees = [
        attendee(
            i, args.base_url, deadline, args.think, metrics, outcomes, random.Random(rng.random())
        )
        for i in range(args.attendees)
    ]
    dashboard = asyncio.create_task(presenter_dashboard(args.base_url, deadline, metrics))
    started = time.monotonic()
    moves = await asyncio.gather(*attendees)
    dashboard.cancel()
    elapsed = time.monotonic() - started

    print(f"\n{args.attendees} attendees, {elapsed:.0f}s wall clock")
    print(f"moves recorded: {sum(moves)} ({sum(moves) / elapsed:.1f}/s)")
    print(metrics.report())
    verdict = build_verdict(
        metrics.samples.get(MODEL_MOVE_ENDPOINT, []), dict(outcomes), args.turn_deadline
    )
    for line in verdict.lines:
        print(line)

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:
        room = await client.get("/presenter/games")
        if room.status_code == 200:
            body = room.json()
            print(
                f"dashboard: {body['playing']} playing, {body['finished']} finished, "
                f"{body['total_dataset_rows']} dataset rows"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attendees", type=int, default=20)
    parser.add_argument("--duration", type=float, default=60.0, help="seconds")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--think", type=float, default=3.0, help="mean pause between exchanges")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--turn-deadline",
        type=float,
        default=deadline_seconds(),
        help="seconds the verdict compares model-move p95 against "
        "(default: this environment's MODEL_TURN_DEADLINE_SECONDS)",
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

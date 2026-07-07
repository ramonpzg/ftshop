"""Simulates a room of attendees hammering a running backend.

Each simulated attendee does what the real UI does: joins, gets a
workspace, starts a timed match, plays legal moves with think time in
between, triggers the model's reply and the per-exchange position
assessment, and polls presenter state every three seconds. One extra
client polls the presenter dashboard. At the end it prints per-endpoint
latency percentiles and error counts.

    just start-backend            # terminal 1, pointed at just mock-llm
    just mock-llm                 # terminal 2
    just load-test 40 60          # terminal 3: 40 attendees, 60 seconds

Without an LLM configured on the backend the sim plays both sides
itself, which still exercises moves, dataset writes, and polling, just
not the thread-holding upstream calls.
"""

import argparse
import asyncio
import random
import time
from collections import defaultdict

import chess
import httpx

PRESENTER_POLL_SECONDS = 3.0


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
            errors = sum(1 for _, status in rows if status >= 500 or status == 0)

            def pct(q: float, latencies: list[float] = latencies) -> float:
                return latencies[min(len(latencies) - 1, int(q * len(latencies)))]

            lines.append(
                f"{endpoint:<28} {len(rows):>6} {errors:>5} "
                f"{pct(0.50):>6.0f}ms {pct(0.95):>6.0f}ms {pct(0.99):>6.0f}ms "
                f"{latencies[-1]:>7.0f}ms"
            )
        return "\n".join(lines)


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

        fen = await start_game()
        while time.monotonic() < deadline and fen is not None:
            board = chess.Board(fen)
            if not board.legal_moves:
                fen = await start_game()
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

            if llm_ready:
                reply = await timed(
                    metrics,
                    "POST model-move",
                    client,
                    "POST",
                    f"/workspaces/{wid}/model-move",
                )
                if reply is not None and reply.status_code == 200:
                    reply_body = reply.json()
                    moves_played += 1
                    if reply_body["move"]["is_legal"]:
                        fen = reply_body["move"]["fen_after"]
                    if reply_body["game_result"]:
                        fen = await start_game()
                        continue
                # The UI refreshes the analysis after every exchange.
                await timed(metrics, "POST assess", client, "POST", f"/workspaces/{wid}/assess")

            await asyncio.sleep(rng.uniform(think * 0.5, think * 1.5))

        poller.cancel()
    return moves_played


async def presenter_dashboard(base: str, deadline: float, metrics: Metrics) -> None:
    async with httpx.AsyncClient(base_url=base, timeout=30.0) as client:
        while time.monotonic() < deadline:
            await timed(metrics, "GET presenter/games", client, "GET", "/presenter/games")
            await asyncio.sleep(PRESENTER_POLL_SECONDS)


async def run(args: argparse.Namespace) -> None:
    metrics = Metrics()
    deadline = time.monotonic() + args.duration
    rng = random.Random(args.seed)
    attendees = [
        attendee(i, args.base_url, deadline, args.think, metrics, random.Random(rng.random()))
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
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

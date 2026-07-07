"""An OpenAI-compatible mock endpoint for load tests and rehearsal.

Answers chat completions the way the workshop uses them: a legal move
for the opponent prompt, a canned assessment for everything else. The
--delay flag simulates real model latency, which is the whole point
of load testing: a slow upstream is what actually stresses the
backend's thread pool. Threaded, so forty simultaneous requests wait
in parallel instead of in line.

    uv run python -m euro_chess_studio.tools.mock_llm --port 9999 --delay 1.2

Point the backend at it:

    OPENAI_API_KEY=test OPENAI_BASE_URL=http://127.0.0.1:9999 just start-backend
"""

import argparse
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DELAY_SECONDS = 0.0


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        user_text = next(
            (m["content"] for m in body.get("messages", []) if m.get("role") == "user"), ""
        )
        if DELAY_SECONDS > 0:
            time.sleep(DELAY_SECONDS)
        if "Pick one move" in user_text:
            match = re.search(r"Legal moves \(UCI\): ([a-h1-8qrbn, ]+)", user_text)
            move = match.group(1).split(",")[0].strip() if match else "e7e5"
            content = json.dumps({"move": move})
        else:
            content = json.dumps(
                {
                    "assessment": "Balanced position. Development over drama.",
                    "real_world": "Like week one at a new job: show up, make normal moves.",
                }
            )
        payload = {"choices": [{"message": {"role": "assistant", "content": content}}]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        pass


def main() -> None:
    global DELAY_SECONDS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--delay", type=float, default=1.2, help="seconds per reply")
    args = parser.parse_args()
    DELAY_SECONDS = args.delay
    print(f"mock llm on http://127.0.0.1:{args.port}, {args.delay}s per reply")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()

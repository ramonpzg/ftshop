"""Guards against resurrecting retired model references.

Every text-model workflow must use Chat Completions, and the
nonexistent gpt-5.5-mini must not reappear in active sources. Historical
phase handovers and learning guides under notes/ are records of past
work and are deliberately not scanned; notebooks are outside this
phase's boundary.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_ROOTS = [
    REPO_ROOT / "api" / "src",
    REPO_ROOT / "api" / "tests",
    REPO_ROOT / "web" / "src",
    REPO_ROOT / "web" / "tests",
    REPO_ROOT / "web" / "sync-server",
    REPO_ROOT / "deck",
    REPO_ROOT / "docs",
    REPO_ROOT / "artifacts",
]

SCANNED_SUFFIXES = {".py", ".ts", ".tsx", ".vue", ".md", ".json", ".yml", ".yaml", ".toml"}
SKIPPED_PARTS = {"node_modules", ".venv", "__pycache__", "generated"}

# gpt-5.5 in any spelling, and the Responses API's telltale call shapes.
FORBIDDEN = ["gpt-5.5", "v1/responses", "client.responses", "responses.create"]


def scannable_files():
    for root in ACTIVE_ROOTS:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
                continue
            if any(part in SKIPPED_PARTS for part in path.parts):
                continue
            yield path


def test_no_stale_model_or_responses_api_references():
    this_file = Path(__file__).resolve()
    offenders = []
    for path in scannable_files():
        if path.resolve() == this_file:
            continue
        text = path.read_text(errors="ignore")
        for token in FORBIDDEN:
            if token in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
    assert offenders == [], "retired references found:\n" + "\n".join(offenders)


def test_the_transport_calls_chat_completions():
    transport = (
        REPO_ROOT / "api" / "src" / "euro_chess_studio" / "data" / "llm_client.py"
    ).read_text()
    assert "/chat/completions" in transport

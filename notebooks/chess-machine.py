import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # From your game to training data

        This notebook runs in your browser. It loads the exact file the
        Export dataset button writes, so what you see here is the room's
        games, not a canned example.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import json
    import urllib.request

    try:
        with urllib.request.urlopen("/api/datasets/text/chess_sft.jsonl") as response:
            lines = response.read().decode().strip().split("\n")
        rows = [json.loads(line) for line in lines if line]
    except Exception:
        rows = []
    mo.md(
        f"**{len(rows)} training rows loaded.** "
        "Empty? Play moves on the board, click Export dataset, rerun this cell."
    )
    return (rows,)


@app.cell
def _(mo, rows):
    sample = rows[0] if rows else {"prompt": "(no rows yet)", "completion": "{}"}
    mo.md(f"One row, exactly as the trainer sees it:\n\n```\n{sample['prompt']}\n```\n\nCompletion: `{sample['completion']}`")
    return


@app.cell
def _(mo, rows):
    prompt_lengths = [len(row["prompt"]) for row in rows] or [0]
    mo.md(
        f"Prompt lengths: min {min(prompt_lengths)}, max {max(prompt_lengths)}, "
        f"mean {sum(prompt_lengths) / len(prompt_lengths):.0f} characters. "
        "Length distribution decides your sequence length, and sequence length "
        "decides your memory bill."
    )
    return


@app.cell
def _(mo):
    def compute_reward(*, legal: bool, is_check: bool, is_checkmate: bool) -> int:
        if not legal:
            return -1
        if is_checkmate:
            return 10
        if is_check:
            return 2
        return 1

    demo = [
        ("illegal move", compute_reward(legal=False, is_check=False, is_checkmate=False)),
        ("quiet move", compute_reward(legal=True, is_check=False, is_checkmate=False)),
        ("check", compute_reward(legal=True, is_check=True, is_checkmate=False)),
        ("checkmate", compute_reward(legal=True, is_check=True, is_checkmate=True)),
    ]
    mo.md(
        "The reward function, the literal one the backend runs:\n\n"
        + "\n".join(f"- {name}: **{value:+d}**" for name, value in demo)
    )
    return


if __name__ == "__main__":
    app.run()

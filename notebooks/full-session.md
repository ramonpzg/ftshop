---
title: Full Session
marimo-version: 0.23.13
width: medium
header: |-
  # /// script
  # requires-python = ">=3.11"
  # dependencies = [
  #     "marimo>=0.23",
  #     "numpy>=2",
  #     "matplotlib>=3.8",
  #     "python-chess>=1.999",
  #     "httpx>=0.28",
  #     "jinja2>=3.1",
  #     "flax>=0.11",
  #     "optax>=0.2",
  # ]
  # ///
  # The whole session as one notebook. Run it live with:
  #
  #     uvx marimo edit --sandbox notebooks/full-session.py
  #
  # Optional extras it detects and uses when present: OPENAI_API_KEY (model
  # opponent, real-world mapping, VLM judge), FAL_KEY (image and video
  # generation), torch+transformers (local audio), modal (GPU sandbox).
---

```python {.marimo}
import marimo as mo

mo.md(
    """
    # Same Recipe, Different Results

    Fine-tuning across text, image, audio, and video. One domain:
    chess. This notebook is the whole session as code. If the
    whiteboard app dies on stage, or you grabbed this file a month
    later, everything is here.

    The recipe never changes: data in pairs, a base model, an
    adapter, an eval. What changes per modality is what "a pair"
    means, how much data it takes, and how it fails. Watch for that.

    Cells that need an API key or a heavy dependency check first and
    tell you what to set instead of erroring.
    """
)
```

```python {.marimo}
import importlib.util
import json
import os

import httpx

def _has(pkg: str) -> bool:
    return importlib.util.find_spec(pkg) is not None

CAPS = {
    "openai_key": bool(os.environ.get("OPENAI_API_KEY")),
    "fal_key": bool(os.environ.get("FAL_KEY")),
    "torch": _has("torch") and _has("transformers"),
    "flax": _has("flax"),
    "modal": _has("modal"),
    "imageio": _has("imageio"),
}
_rows = "\n".join(
    f"| {name} | {'yes' if ok else 'no'} |"
    for name, ok in [
        ("OPENAI_API_KEY (opponent, mapping, judge)", CAPS["openai_key"]),
        ("FAL_KEY (image and video generation)", CAPS["fal_key"]),
        ("torch + transformers (local audio)", CAPS["torch"]),
        ("flax (live JAX training)", CAPS["flax"]),
        ("modal (GPU sandbox)", CAPS["modal"]),
    ]
)
mo.md(f"**What runs on this machine right now:**\n\n| capability | ready |\n|---|---|\n{_rows}")
```

## 1. Why chess

AI has beaten grandmasters for decades and chess has never been
more popular. It is the perfect fine-tuning domain for one
reason: **the environment can validate every action**. A move is
legal or it is not; python-chess decides in microseconds; no
human labeler required. That single property gives us free
supervision for SFT and a free reward signal for RL.

And the personal angle, which becomes the dataset's unique
angle later: everyone can mould their own instructor. Mine
should teach me to win while capturing as few pieces as
possible.

````python {.marimo}
import chess

game_board = chess.Board()
# A scripted Ruy Lopez so the notebook is deterministic without keys.
game_sans = ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O"]
game_records = []
for _san in game_sans:
    _fen_before = game_board.fen()
    _legal_before = [m.uci() for m in game_board.legal_moves]
    _move = game_board.push_san(_san)
    game_records.append(
        {
            "san": _san,
            "uci": _move.uci(),
            "fen_before": _fen_before,
            "fen_after": game_board.fen(),
            "legal_moves_before": _legal_before,
            "is_check": game_board.is_check(),
            "is_checkmate": game_board.is_checkmate(),
        }
    )
mo.md(
    f"## 2. Building a Chess Machine\n\nA game to work with. {len(game_records)} plies of a "
    f"Ruy Lopez, ending here:\n\n```\n{game_board.unicode(invert_color=True)}\n```\n\n"
    "Every row of training data in this section comes from this game, "
    "the same way the app builds rows from yours."
)
````

```python {.marimo}
def compute_reward(*, legal: bool, is_check: bool, is_checkmate: bool) -> int:
    if not legal:
        return -1
    if is_checkmate:
        return 10
    if is_check:
        return 2
    return 1

def is_legal_move(fen: str, uci: str) -> bool:
    _board = chess.Board(fen)
    try:
        return chess.Move.from_uci(uci) in _board.legal_moves
    except ValueError:
        return False

_start = chess.STARTING_FEN
mo.md(
    "### The reward function\n\n"
    "SFT teaches the model what good answers look like. RL teaches it "
    "what good actions do. Chess prices actions for free:\n\n"
    f"- illegal (e2e5 from the start): **{compute_reward(legal=is_legal_move(_start, 'e2e5'), is_check=False, is_checkmate=False):+d}**\n"
    f"- legal quiet move (e2e4): **{compute_reward(legal=is_legal_move(_start, 'e2e4'), is_check=False, is_checkmate=False):+d}**\n"
    "- check: **+2**, checkmate: **+10**\n\n"
    "Four lines of Python. That is the entire reward model. Envy your "
    "colleagues in robotics later."
)
```

````python {.marimo}
def format_pgn_prefix(sans: list[str]) -> str:
    _parts = []
    for _i, _san in enumerate(sans):
        _parts.append(f"{_i // 2 + 1}. {_san}" if _i % 2 == 0 else _san)
    return " ".join(_parts)

def build_dataset_rows(prior_sans, record) -> list[dict]:
    _reward = compute_reward(
        legal=True, is_check=record["is_check"], is_checkmate=record["is_checkmate"]
    )
    return [
        {"shape": "pgn_prefix_to_move", "payload": {"prefix": format_pgn_prefix(prior_sans), "target_san": record["san"]}},
        {"shape": "fen_to_move", "payload": {"fen": record["fen_before"], "target_uci": record["uci"]}},
        {"shape": "fen_legal_moves_to_move", "payload": {"fen": record["fen_before"], "legal_moves": record["legal_moves_before"], "target_uci": record["uci"]}},
        {"shape": "board_tensor_to_move_class", "payload": {"tensor_shape": [8, 8, 12], "target_move_class": record["uci"], "note": "the serious supervised path: 12 binary planes, not a string"}},
        {"shape": "policy_value_to_move", "payload": {"policy_target": {u: (1.0 if u == record["uci"] else 0.0) for u in record["legal_moves_before"][:6]}, "value_target": _reward / 10, "note": "policy over legal moves plus a scalar value, the engine path"}},
        {"shape": "rl_trajectory", "payload": {"state_fen": record["fen_before"], "action_uci": record["uci"], "reward": _reward, "next_state_fen": record["fen_after"], "done": False}},
    ]

all_rows = []
_sans_so_far = []
for _rec in game_records:
    all_rows.extend(build_dataset_rows(_sans_so_far, _rec))
    _sans_so_far.append(_rec["san"])

mo.md(
    "### One move, six dataset shapes\n\n"
    "The same position encoded the way each training approach eats it. "
    f"Our {len(game_records)}-ply game just became **{len(all_rows)} rows**. "
    "The first move, all six ways:\n\n"
    "```json\n"
    + "\n".join(json.dumps({r['shape']: r['payload']}, default=str)[:170] for r in all_rows[:6])
    + "\n```\n\nSame game. Six framings. Same recipe, different results starts here."
)
````

````python {.marimo}
PROMPT_TEMPLATE = (
    "You are a chess engine assistant.\n\n"
    "Position (FEN): {fen}\n"
    "Legal moves (UCI): {legal_moves}\n\n"
    "Return exactly one move from the legal moves list, in UCI format.\n"
    'Respond with JSON: {{"move": "<uci>"}}'
)

from jinja2 import Template

CHAT_TEMPLATE = Template(
    "{% for message in messages %}<|{{ message.role }}|>\n{{ message.content }}\n{% endfor %}<|assistant|>\n"
)
_rendered = CHAT_TEMPLATE.render(
    messages=[
        {"role": "system", "content": "You are a chess engine assistant."},
        {"role": "user", "content": "Position (FEN): ..."},
    ]
)
mo.md(
    "### Templates, the part everyone fumbles\n\n"
    "The prompt template is what you write. The **chat template** is "
    "what the tokenizer actually renders, and it is Jinja:\n\n"
    f"```\n{_rendered}\n```\n\n"
    "Every model family ships its own. Fine-tune with the wrong one and "
    "the model learns to answer a format nobody sends. This is the "
    "single most common silent failure in text fine-tuning."
)
````

```python {.marimo}
def llm_chat(messages: list[dict], json_mode: bool = True) -> str:
    """One OpenAI-compatible chat call. Swap the endpoint by env var."""
    _base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    _body = {"model": os.environ.get("OPENAI_MODEL", "gpt-5.5-mini"), "messages": messages}
    if json_mode:
        _body["response_format"] = {"type": "json_object"}
    with httpx.Client(timeout=60) as _client:
        _r = _client.post(
            f"{_base}/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json=_body,
        )
        if _r.status_code == 400 and json_mode:
            _body.pop("response_format")
            _r = _client.post(
                f"{_base}/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                json=_body,
            )
        _r.raise_for_status()
    return _r.json()["choices"][0]["message"]["content"]

def parse_move_reply(text: str) -> str | None:
    try:
        _move = json.loads(text.strip().strip("`").removeprefix("json")).get("move", "")
    except json.JSONDecodeError:
        return None
    return _move.strip().lower() or None

mo.md(
    "### A model that plays\n\n"
    "The client is 25 lines because the endpoint is a commodity: "
    "api.openai.com today, a Hugging Face router tomorrow, vLLM on "
    "your own box next month. Same code, different `OPENAI_BASE_URL`."
    + ("" if CAPS["openai_key"] else "\n\n*Set OPENAI_API_KEY to run the next two cells.*")
)
```

```python {.marimo}
llm_game_log = []
if CAPS["openai_key"]:
    _board = chess.Board()
    for _ply in range(4):
        _legal = [m.uci() for m in _board.legal_moves]
        _reply = llm_chat(
            [
                {"role": "system", "content": "You play chess. JSON only."},
                {"role": "user", "content": PROMPT_TEMPLATE.format(fen=_board.fen(), legal_moves=", ".join(_legal))},
            ]
        )
        _uci = parse_move_reply(_reply)
        _legal_choice = _uci in _legal
        _reward = compute_reward(legal=_legal_choice, is_check=False, is_checkmate=False)
        llm_game_log.append(f"ply {_ply + 1}: model played `{_uci}`, reward {_reward:+d}")
        if not _legal_choice:
            llm_game_log.append("the environment caught it. The board does not move.")
            break
        _board.push_uci(_uci)
    _body = "\n".join(f"- {line}" for line in llm_game_log)
    _out = mo.md(f"**The model plays itself for four plies:**\n\n{_body}")
else:
    _out = mo.md("*Skipped: no OPENAI_API_KEY. The model would play here, and every illegal choice would earn -1 live.*")
mo.vstack(
    [
        _out,
        mo.md(
            "In the whiteboard app this is a timed match: five minutes on "
            "the clock by default, thirty at most. Starting over counts as "
            "a loss, and so does the flag falling. The Duolingo rule: "
            "quitting has a price, so people stop quitting, so the dataset "
            "keeps growing."
        ),
    ]
)
```

```python {.marimo}
real_world_maps = []
if CAPS["openai_key"]:
    for _rec in [game_records[1], game_records[4]]:
        _reply = llm_chat(
            [
                {"role": "system", "content": "Chess commentator. Terse. You map positions to everyday scenarios. JSON only."},
                {"role": "user", "content": f'Position after {_rec["san"]} (FEN {_rec["fen_after"]}). Respond {{"assessment": "...", "real_world": "..."}}'},
            ]
        )
        try:
            real_world_maps.append((_rec["san"], json.loads(_reply)))
        except json.JSONDecodeError:
            pass
    _lines = "\n".join(
        f"- after **{r}**: {m.get('assessment', '')} *{m.get('real_world', '')}*"
        for r, m in real_world_maps
    )
    _out2 = mo.md(f"### The unique angle: games as life\n\n{_lines}\n\nA hundred of these mappings is a dataset nobody else has. That, not the chess engine, is what makes your fine-tune yours.")
else:
    _out2 = mo.md(
        "### The unique angle: games as life\n\n*Skipped: no OPENAI_API_KEY.* "
        "With a key, each position gets mapped to an everyday scenario "
        "(the pinned knight as the colleague who cannot say no). A "
        "hundred such rows is the dataset nobody else has."
    )
_out2
```

```python {.marimo}
from pathlib import Path

sft_rows = [
    {
        "prompt": PROMPT_TEMPLATE.format(fen=_r["payload"]["fen"], legal_moves=", ".join(_r["payload"]["legal_moves"])),
        "completion": json.dumps({"move": _r["payload"]["target_uci"]}),
    }
    for _r in all_rows
    if _r["shape"] == "fen_legal_moves_to_move"
]

# Bridge to the app: prefer the file the Export dataset button writes.
sft_path = Path("data/processed/text/chess_sft.jsonl")
if sft_path.is_file():
    sft_rows = [json.loads(line) for line in sft_path.read_text().strip().split("\n")]
    _source = f"loaded **{len(sft_rows)} rows from the app's export** at `{sft_path}`"
else:
    sft_path = Path(os.environ.get("TMPDIR", "/tmp")) / "chess_sft.jsonl"
    sft_path.write_text("\n".join(json.dumps(r) for r in sft_rows) + "\n")
    _source = f"wrote **{len(sft_rows)} rows** from the scripted game to `{sft_path}`"

mo.md(
    f"### Export: the file every trainer loads\n\nprompt/completion JSONL, {_source}. "
    "The Unsloth run, the Axolotl config, and the JAX loop below all "
    "point at this one file. Play on the whiteboard, train here."
)
```

```python {.marimo}
_legal_rate = 1.0  # scripted game: every recorded move was legal by construction
_json_ok = sum(
    1
    for _r in all_rows
    if _r["shape"] == "fen_legal_moves_to_move"
    and parse_move_reply(json.dumps({"move": _r["payload"]["target_uci"]}))
)
_json_total = sum(1 for _r in all_rows if _r["shape"] == "fen_legal_moves_to_move")
mo.md(
    "### Evals before training, not after\n\n"
    f"- legal move rate: **{_legal_rate:.2f}** (the metric the model opponent gets judged on)\n"
    f"- valid JSON rate: **{_json_ok / _json_total:.2f}**\n"
    "- centipawn loss and mate-in-one need Stockfish: "
    "`chess.engine.SimpleEngine.popen_uci('stockfish')`, then "
    "`engine.analyse(board, limit)` per position. Install Stockfish and "
    "those two metrics come free.\n\n"
    "If you cannot measure the base model, you cannot claim the "
    "fine-tune helped. Evals are the first cell you write, not the last."
)
```

### The training ladder

Five rungs, most to least abstracted. Same dataset every time.

1. **UI**: Unsloth Studio, `unsloth studio -p 8888`. No code,
   live loss curves, GGUF export.
2. **API**: a training endpoint (Thinking Machines and friends).
   Your data leaves the room; your GPU budget does not.
3. **Config**: Axolotl. The run is a YAML file (next cell).
4. **Code that reads like config**: Unsloth or PEFT (cell after).
5. **As low as it goes**: JAX. You write the loss. It runs live
   in this notebook on CPU.

Past SFT: the reward function plus legality checking here is a
minimal RL environment, hand-rolled so it fits on a slide. The
production-grade version of the same idea (env classes, rubrics,
rollouts, GRPO training) is the verifiers library:
github.com/PrimeIntellect-ai/verifiers.

````python {.marimo}
axolotl_yaml = f"""# axolotl train chess-lora.yml    (NVIDIA Ampere+ or AMD only)
base_model: google/gemma-4-E2B-it
load_in_4bit: true
adapter: lora
lora_r: 16
lora_alpha: 32

chat_template: gemma4
datasets:
  - path: {sft_path}
type:
  field_instruction: prompt
  field_output: completion
  format: "{{instruction}}"
  no_input_format: "{{instruction}}"

sequence_len: 2048
micro_batch_size: 1
gradient_accumulation_steps: 4
num_epochs: 1
learning_rate: 0.0002
output_dir: ./outputs/chess-lora
"""
mo.md(f"### Rung 3: the run is a file\n\n```yaml\n{axolotl_yaml}```")
````

````python {.marimo}
unsloth_code = f'''from datasets import load_dataset
from trl import SFTConfig, SFTTrainer
from unsloth import FastModel

dataset = load_dataset("json", data_files="{sft_path}", split="train")

model, tokenizer = FastModel.from_pretrained(
model_name="unsloth/gemma-4-E2B-it", max_seq_length=2048, load_in_4bit=True
)
model = FastModel.get_peft_model(model, r=8, lora_alpha=8)

SFTTrainer(
model=model, tokenizer=tokenizer, train_dataset=dataset,
args=SFTConfig(per_device_train_batch_size=1, gradient_accumulation_steps=4,
               max_steps=60, learning_rate=2e-4, output_dir="outputs/chess-lora"),
).train()'''
mo.md(
    "### Rung 4: code that reads like config\n\n"
    f"```python\n{unsloth_code}\n```\n\n"
    "Gemma 4 E2B, 4-bit, LoRA rank 8: fits in 8GB of VRAM. Sixty steps "
    "on a hundred rows is a real, visible fine-tune. Run it on your "
    "GPU, in Unsloth Studio, or in the sandbox two cells down."
)
````

```python {.marimo}
jax_result = None
if CAPS["flax"]:
    import numpy as _np
    import optax
    from flax import nnx

    # Tokenize UCI moves: one token per character, tiny vocab.
    _vocab = {c: i + 1 for i, c in enumerate("abcdefgh12345678qrbn")}
    _seqs = [
        [0] + [_vocab[c] for c in r["payload"]["target_uci"]]
        for r in all_rows
        if r["shape"] == "fen_to_move"
    ]
    _maxlen = max(len(s) for s in _seqs) + 1
    _data = _np.zeros((len(_seqs), _maxlen), dtype=_np.int32)
    for _i, _s in enumerate(_seqs):
        _data[_i, : len(_s)] = _s

    class TinyLM(nnx.Module):
        def __init__(self, vocab, dim=64, rngs=nnx.Rngs(0)):
            self.embed = nnx.Embed(vocab, dim, rngs=rngs)
            self.attn = nnx.MultiHeadAttention(num_heads=4, in_features=dim, decode=False, rngs=rngs)
            self.norm = nnx.LayerNorm(dim, rngs=rngs)
            self.head = nnx.Linear(dim, vocab, rngs=rngs)

        def __call__(self, tokens):
            x = self.embed(tokens)
            x = x + self.attn(self.norm(x), mask=nnx.make_causal_mask(tokens))
            return self.head(x)

    jax_model = TinyLM(vocab=len(_vocab) + 1)
    _optimizer = nnx.Optimizer(jax_model, optax.adamw(3e-3), wrt=nnx.Param)

    @nnx.jit
    def _train_step(model, optimizer, tokens):
        def _loss_fn(model):
            _logits = model(tokens[:, :-1])
            return optax.softmax_cross_entropy_with_integer_labels(_logits, tokens[:, 1:]).mean()

        _loss, _grads = nnx.value_and_grad(_loss_fn)(model)
        optimizer.update(model, _grads)
        return _loss

    jax_losses = [float(_train_step(jax_model, _optimizer, _data)) for _ in range(150)]
    jax_result = (jax_losses[0], jax_losses[-1])

    import matplotlib.pyplot as _plt

    _fig, _ax = _plt.subplots(figsize=(6, 2.2))
    _ax.plot(jax_losses, color="#212529")
    _ax.set_xlabel("step")
    _ax.set_ylabel("loss")
    _ax.set_title(f"a language model training, live, on this CPU: {jax_result[0]:.2f} to {jax_result[1]:.2f}")
    _out3 = mo.vstack(
        [
            mo.md(
                "### Rung 5: no trainer, no config, just the loss\n\n"
                "A 4-layer-of-code transformer learning the *shape* of UCI "
                "moves from our game, right now, in this cell. It learns the "
                "format in seconds. It does not learn chess. That gap, format "
                "is cheap, competence is not, is the honest one-line summary "
                "of small fine-tunes."
            ),
            _fig,
        ]
    )
else:
    _out3 = mo.md("### Rung 5: JAX\n\n*Skipped: flax not installed. With it, a tiny transformer trains here, live, on CPU, in seconds.*")
_out3
```

````python {.marimo}
modal_code = '''import modal

app = modal.App("chess-lora")
image = modal.Image.debian_slim().pip_install("unsloth", "trl", "datasets")

@app.function(gpu="L40S", image=image, timeout=1800,
          secrets=[modal.Secret.from_name("huggingface")])
def train(jsonl: bytes):
open("chess_sft.jsonl", "wb").write(jsonl)
# ... the exact Unsloth cell from above ...

# modal run train_chess.py'''
_configured = CAPS["modal"] and bool(os.environ.get("MODAL_TOKEN_ID"))
mo.md(
    "### Borrowed GPUs: sandboxes\n\n"
    "No GPU in the room? Ship the same code to one. Modal is the "
    "shortest path; Daytona, Docker sandboxes (sbx), and Dify "
    "sandboxes all fit the same hole: your JSONL in, an adapter out.\n\n"
    f"```python\n{modal_code}\n```\n\n"
    + ("Modal is configured on this machine: `modal run` away." if _configured else "*Install modal and run `modal token new` to use this live.*")
)
````

## 3. Painting Our Pieces (image)

Same recipe. New failure modes.

Diffusion models denoise toward your caption; transformers
predict tokens. Both fine-tune with LoRA, but image adaptation
is far more sensitive to **dataset size and composition** than
text: twenty consistent images beat two hundred sloppy ones.
Providers also quietly rewrite your prompts before generation,
which is why your local results differ from their playground.

The approach menu, each one a different data recipe: text to
image, image to image, image plus text to image, text to SVG,
image to SVG, image editing, image layering.

```python {.marimo}
img_trigger = mo.ui.text(value="wtrclrchess", label="Trigger word")
img_trigger
```

```python {.marimo}
img_captions = [
    f"a {img_trigger.value} style {piece}, soft watercolor edges, plain background"
    for piece in ["white knight", "black queen", "white bishop", "black rook"]
]
mo.md(
    "**Captions are the dataset.** The trigger word is a new token the "
    "model binds to your style; consistency is what does the binding:\n\n"
    + "\n".join(f"- `{c}`" for c in img_captions)
    + "\n\nHold one aspect ratio too, or the model learns that your style stretches."
)
```

```python {.marimo}
import time

def fal_run(model_id: str, payload: dict, timeout: float = 600.0) -> dict:
    """fal queue API: submit, poll the returned urls, fetch."""
    _headers = {"Authorization": f"Key {os.environ['FAL_KEY']}"}
    with httpx.Client(timeout=60) as _client:
        _sub = _client.post(f"https://queue.fal.run/{model_id}", headers=_headers, json=payload)
        _sub.raise_for_status()
        _urls = _sub.json()
        _deadline = time.monotonic() + timeout
        while True:
            _status = _client.get(_urls["status_url"], headers=_headers).json()["status"]
            if _status == "COMPLETED":
                break
            if _status not in ("IN_QUEUE", "IN_PROGRESS") or time.monotonic() > _deadline:
                raise RuntimeError(f"fal job state: {_status}")
            time.sleep(1)
        return _client.get(_urls["response_url"], headers=_headers).json()

img_url = None
if CAPS["fal_key"]:
    _result = fal_run(
        "fal-ai/flux-2/klein/4b",
        {"prompt": img_captions[0], "image_size": "square_hd", "num_images": 1},
    )
    img_url = _result["images"][0]["url"]
    _out4 = mo.vstack(
        [
            mo.md(f"**FLUX.2 Klein 4B, ~$0.005 and a few seconds:** `{img_captions[0]}`"),
            mo.image(img_url, width=380),
            mo.md("Swap the model id to `fal-ai/flux/schnell` for the cheap-and-fast comparison."),
        ]
    )
else:
    _out4 = mo.md("**Generation.** *Skipped: no FAL_KEY.* With one, FLUX.2 Klein 4B renders the first caption here for about half a cent.")
_out4
```

````python {.marimo}
if CAPS["openai_key"] and img_url:
    _judge = llm_chat(
        [
            {"role": "user", "content": [
                {"type": "text", "text": f'Judge this image against the caption "{img_captions[0]}". Respond JSON {{"piece_identity": 0-1, "prompt_adherence": 0-1, "note": "..."}}'},
                {"type": "image_url", "image_url": {"url": img_url}},
            ]},
        ]
    )
    try:
        _scores = json.loads(_judge)
    except json.JSONDecodeError:
        _scores = {"note": _judge[:200]}
    _out5 = mo.md(f"**VLM as judge** (the image evals: piece identity, style consistency, prompt adherence, caption sensitivity, human preference):\n\n```json\n{json.dumps(_scores, indent=1)}\n```")
else:
    _out5 = mo.md(
        "**Image evals**: piece identity, style consistency, prompt "
        "adherence, caption sensitivity, human preference. The first "
        "four automate with a VLM judge (this cell runs one when both "
        "keys are set); the last one is you, squinting."
    )
_out5
````

**Training the style**: the same LoRA recipe through Diffusers,
pointed at your drawings.

```bash
accelerate launch train_dreambooth_lora_flux.py \
  --pretrained_model_name_or_path black-forest-labs/FLUX.2-Klein-4B \
  --instance_data_dir ./drawings \
  --instance_prompt "a wtrclrchess style chess piece" \
  --rank 16 --max_train_steps 800 --learning_rate 1e-4
```

The code ladder repeats: a UI, then stablediffusion.cpp, then
Diffusers. Recognize the shape from the text section. That is
the point.

```python {.marimo}
import numpy as np

aud_rate = 16000
_t = np.linspace(0, 0.3, int(aud_rate * 0.3), endpoint=False)
aud_wave = np.exp(-_t * 30) * (
    0.7 * np.sin(2 * np.pi * 820 * _t) + 0.3 * np.sin(2 * np.pi * 1750 * _t)
)

import io
import wave as _wave_module

_buf = io.BytesIO()
with _wave_module.open(_buf, "wb") as _f:
    _f.setnchannels(1)
    _f.setsampwidth(2)
    _f.setframerate(aud_rate)
    _f.writeframes((aud_wave * 32767).astype(np.int16).tobytes())
aud_click_wav = _buf.getvalue()

import matplotlib.pyplot as _plt2

_fig2, _ax2 = _plt2.subplots(figsize=(6, 2.4))
_ax2.specgram(aud_wave, Fs=aud_rate, NFFT=256, noverlap=128)
_ax2.set_title("a wooden capture click, as the picture a model trains on")
mo.vstack(
    [
        mo.md(
            "## 4. Giving the Board Sound (audio)\n\n"
            "Sound is vibration, audio is its recording, and a spectrogram "
            "turns the recording into an image. From there the recipe splits: "
            "MusicGen predicts audio tokens like an LLM predicts words; "
            "Stable Audio denoises like an image model. Same recipe, "
            "different substrate. First, a capture click from raw sine waves:"
        ),
        mo.audio(aud_click_wav),
        _fig2,
    ]
)
```

```python {.marimo}
aud_generated = None
if CAPS["torch"]:
    from transformers import pipeline as _hf_pipeline

    _synth = _hf_pipeline("text-to-audio", "facebook/musicgen-small")
    _music = _synth(
        "tense chess endgame music, low strings, ticking clock",
        forward_params={"do_sample": True, "max_new_tokens": 256},
    )
    import io as _io2

    import scipy.io.wavfile as _wavfile

    _buf2 = _io2.BytesIO()
    _wavfile.write(_buf2, rate=_music["sampling_rate"], data=_music["audio"])
    aud_generated = _buf2.getvalue()
    _out6 = mo.vstack(
        [
            mo.md("**MusicGen small (0.6B), locally, on this machine.** Five seconds of endgame tension (first run downloads ~2.4GB):"),
            mo.audio(aud_generated),
        ]
    )
else:
    _out6 = mo.md(
        "**Local generation.** *Skipped: torch + transformers not "
        "installed.* With them, musicgen-small (0.6B) generates endgame "
        "music right here; stable-audio-open-1.0 does sound effects via "
        "diffusion. The narrator idea (let's get ready to rumble) is a "
        "TTS fine-tune with the same recipe again."
    )
_out6
```

```python {.marimo}
_wav = aud_generated or aud_click_wav
_samples = np.frombuffer(_wav[44:], dtype=np.int16).astype(np.float32) / 32767
_duration = len(_samples) / (32000 if aud_generated else aud_rate)
_clipping = float(np.mean(np.abs(_samples) > 0.985))
mo.md(
    "**Audio evals, computed on the clip above, not invented:**\n\n"
    f"- duration: **{_duration:.2f}s** (duration error = |target - actual|)\n"
    f"- clipping rate: **{_clipping:.4f}** (samples at the rail)\n"
    "- tag similarity and event recognisability: embed with "
    "panns-inference, cosine against the prompt tags\n"
    "- human preference: still you, still squinting"
)
```

```python {.marimo}
vid_total_frames, vid_samples = 150, 8
vid_indices = [int(i * vid_total_frames / vid_samples) for i in range(vid_samples)]

import matplotlib.pyplot as _plt3

_fig3, _ax3 = _plt3.subplots(figsize=(6, 1.4))
_ax3.vlines(np.arange(vid_total_frames), 0, 0.3, colors="#dee2e6")
_ax3.vlines(vid_indices, 0, 1, colors="#212529", linewidths=2)
_ax3.set_yticks([])
_ax3.set_xlabel("frame index. dark = what the model sees")
mo.vstack(
    [
        mo.md(
            "## 5. Video of the Real-World Use Case\n\n"
            "The least documented modality. A model cannot eat every frame, "
            f"so it samples: {vid_samples} of {vid_total_frames} frames here, "
            f"**{vid_samples / vid_total_frames:.0%} of the clip**, and it must "
            "hallucinate the rest coherently. Temporal consistency is the "
            "failure mode; compute escalates faster than you expect.\n\n"
            "The plan: take the hundred real-world mapping prompts from the "
            "text section, generate clips with a frontier model, fine-tune "
            "LTX on the result. Distillation by another name."
        ),
        _fig3,
    ]
)
```

```python {.marimo}
vid_url = None
if CAPS["fal_key"]:
    _vresult = fal_run(
        "fal-ai/ltx-2.3/text-to-video/fast",
        {"prompt": "a knight fork winning a queen, top-down wooden chess board, soft light", "duration": 6, "resolution": "1080p", "fps": 25},
    )
    vid_url = _vresult["video"]["url"]
    _out7 = mo.vstack(
        [
            mo.md("**LTX 2.3 fast: six seconds, about $0.24, one long minute.** Say the price out loud, it is the lesson: video costs cents per second where images cost fractions of a cent each."),
            mo.video(vid_url),
        ]
    )
else:
    _out7 = mo.md(
        "**Generation.** *Skipped: no FAL_KEY.* With one, LTX 2.3 fast "
        "renders a knight fork here for ~$0.24; swap the id to "
        "`fal-ai/veo3.1/fast` for the frontier comparison at 3x the price. "
        "Temporal flicker measures as mean absolute difference between "
        "consecutive sampled frames: high flicker, broken consistency."
    )
_out7
```

## 6. Merging: capabilities without retraining

Once you own several fine-tunes, merging combines them for the
price of an average. mergekit:

```yaml
merge_method: slerp
models:
  - model: outputs/chess-lora        # the player
  - model: outputs/analyst-lora      # the real-world mapper
parameters:
  t: 0.5
```

When it works: adapters trained from the **same base** on
disjoint skills. When it wrecks quality: different bases,
different chat templates, or two adapters fighting over the
same behavior. Merging averages weights, not intentions. Eval
before and after or you merged blind.
<!---->
## Closing

Training any of these from scratch is expensive, and we get open
models matching closed ones from two years ago, sometimes six
months. The barrier keeps dropping: Karpathy's microchat trains
a GPT in a few hundred lines on consumer hardware, and you just
trained a transformer inside a notebook cell.

As compute gets cheaper, specialisation may matter more than a
ten-point benchmark gap. The recipe you now know four times
over: pairs in, adapter out, eval always. Same recipe,
different results, and the results are yours.

**Resources**: python-chess docs, Unsloth docs (Gemma 4 guide),
Axolotl docs, Flax NNX guide, Diffusers LoRA training scripts,
fal.ai model registry, mergekit, marimo, and the workshop repo
this notebook lives in.
/** Real, runnable snippets shown in the mini IDE. Each mirrors the actual
 * backend logic it's teaching, trimmed to something readable standalone. */

export interface Snippet {
  id: string;
  label: string;
  language: "python" | "yaml";
  code: string;
}

export const SNIPPETS: Snippet[] = [
  {
    id: "prompt_template",
    label: "Prompt template",
    language: "python",
    code: `PROMPT_TEMPLATE = """You are a chess engine assistant.

Position (FEN): {fen}
Legal moves (UCI): {legal_moves}

Return exactly one move from the legal moves list, in UCI format.
Respond with JSON: {{"move": "<uci>"}}
"""


def build_prompt(fen: str, legal_moves: list[str]) -> str:
    return PROMPT_TEMPLATE.format(fen=fen, legal_moves=", ".join(legal_moves))


# build_prompt(chess.STARTING_FEN, ["e2e4", "d2d4", "g1f3", ...])
`,
  },
  {
    id: "legal_move_validation",
    label: "Legal move validation",
    language: "python",
    code: `import chess


def is_legal_move(fen: str, uci: str) -> bool:
    board = chess.Board(fen)
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return False
    return move in board.legal_moves


fen = chess.STARTING_FEN
print(is_legal_move(fen, "e2e4"))  # True
print(is_legal_move(fen, "e2e5"))  # False, pawns don't jump two ranks from e2 to e5
`,
  },
  {
    id: "dataset_row_builder",
    label: "Dataset row builder",
    language: "python",
    code: `import chess


def build_fen_to_move_row(fen_before: str, uci: str) -> dict:
    board = chess.Board(fen_before)
    move = chess.Move.from_uci(uci)
    san = board.san(move)
    return {
        "shape": "fen_to_move",
        "payload": {"fen": fen_before, "target_uci": uci, "target_san": san},
    }


row = build_fen_to_move_row(chess.STARTING_FEN, "e2e4")
print(row)
# {"shape": "fen_to_move", "payload": {"fen": "...", "target_uci": "e2e4", "target_san": "e4"}}
`,
  },
  {
    id: "reward_function",
    label: "RL reward function",
    language: "python",
    code: `def compute_reward(*, legal: bool, is_check: bool, is_checkmate: bool) -> int:
    if not legal:
        return -1
    if is_checkmate:
        return 10
    if is_check:
        return 2
    return 1


# SFT teaches the model what good answers look like.
# RL teaches the model what good actions do. This reward is what RL needs,
# and chess is a good RL environment because the environment can validate
# every move for you.
`,
  },
  {
    id: "chat_template",
    label: "Chat template (Jinja)",
    language: "python",
    code: `# What the tokenizer actually renders before training or inference.
# Same Jinja engine as HTML templating, applied to a message list.
CHAT_TEMPLATE = """{% for message in messages %}
<|{{ message.role }}|>
{{ message.content }}
{% endfor %}
<|assistant|>
"""

messages = [
    {"role": "system", "content": "You are a chess engine assistant."},
    {"role": "user", "content": "Position (FEN): ... Legal moves: ..."},
]

# tokenizer.apply_chat_template(messages, tokenize=False)
# Every model family ships its own template. Mismatch it during
# fine-tuning and the model learns to answer a format nobody sends.
`,
  },
  {
    id: "fine_tune",
    label: "Unsloth (LoRA)",
    language: "python",
    code: `from datasets import load_dataset
from trl import SFTConfig, SFTTrainer
from unsloth import FastModel

# The exact file the Export dataset button writes, from the room's games.
dataset = load_dataset(
    "json", data_files="data/processed/text/chess_sft.jsonl", split="train"
)

model, tokenizer = FastModel.from_pretrained(
    model_name="unsloth/gemma-4-E2B-it",
    max_seq_length=2048,
    load_in_4bit=True,
)
model = FastModel.get_peft_model(model, r=8, lora_alpha=8)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=SFTConfig(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=60,
        learning_rate=2e-4,
        output_dir="outputs/chess-lora",
    ),
)
trainer.train()

# Same run, no code: unsloth studio -p 8888
# Same recipe, different results: swap the dataset and the base model,
# keep the shape. The image, audio, and video runs read the same way.
`,
  },
  {
    id: "axolotl_config",
    label: "Axolotl config",
    language: "yaml",
    code: `# The whole run is this file: axolotl train chess-lora.yml
# NVIDIA (Ampere or newer) or AMD GPU required.
base_model: google/gemma-4-E2B-it
load_in_4bit: true
adapter: lora
lora_r: 16
lora_alpha: 32
lora_dropout: 0

chat_template: gemma4
datasets:
  - path: data/processed/text/chess_sft.jsonl
    type:
      field_instruction: prompt
      field_output: completion
      format: "{instruction}"
      no_input_format: "{instruction}"

sequence_len: 2048
micro_batch_size: 1
gradient_accumulation_steps: 4
num_epochs: 1
learning_rate: 0.0002
lr_scheduler: cosine
optimizer: adamw_torch_8bit
bf16: auto
gradient_checkpointing: true
output_dir: ./outputs/chess-lora
`,
  },
  {
    id: "jax_train",
    label: "JAX (low level)",
    language: "python",
    code: `import optax
from flax import nnx


class TinyLM(nnx.Module):
    def __init__(self, vocab, dim=128, rngs=nnx.Rngs(0)):
        self.embed = nnx.Embed(vocab, dim, rngs=rngs)
        self.attn = nnx.MultiHeadAttention(
            num_heads=4, in_features=dim, decode=False, rngs=rngs
        )
        self.norm = nnx.LayerNorm(dim, rngs=rngs)
        self.head = nnx.Linear(dim, vocab, rngs=rngs)

    def __call__(self, tokens):
        x = self.embed(tokens)
        x = x + self.attn(self.norm(x), mask=nnx.make_causal_mask(tokens))
        return self.head(x)


model = TinyLM(vocab=512)
optimizer = nnx.Optimizer(model, optax.adamw(3e-4), wrt=nnx.Param)


@nnx.jit
def train_step(model, optimizer, tokens):
    def loss_fn(model):
        logits = model(tokens[:, :-1])
        return optax.softmax_cross_entropy_with_integer_labels(
            logits, tokens[:, 1:]
        ).mean()

    loss, grads = nnx.value_and_grad(loss_fn)(model)
    optimizer.update(model, grads)
    return loss


# No trainer, no config. The loop is these lines, and it runs on CPU.
# Reads closer to NumPy than PyTorch does, which is the point.
`,
  },
];

export function getSnippetById(id: string): Snippet {
  const snippet = SNIPPETS.find((s) => s.id === id);
  if (!snippet) throw new Error(`unknown snippet id: ${id}`);
  return snippet;
}

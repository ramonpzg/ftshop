# Chess adapter run

This is an offline preparation job, not part of the 90-minute attendee setup.
It builds one reproducible sample, enriches it through Luna, trains a Gemma 4
adapter with Unsloth, validates legal move replies on held-out games, and
uploads the adapter to Hugging Face.

## The laptop command

The whole viable run is one command:

```bash
just chess-adapt
```

With no flags, that means `--prepare --enrich --qlora --push`. It publishes
the adapter to `ramonpzg/gemma-4-e2b-chessking`. It does not attempt bf16
LoRA on this laptop: the base checkpoint is about 10.2 GB before activations
or optimiser state, while the RTX 2000 Ada has 8 GB VRAM.

Run stages separately when the conference connection drops:

```bash
just chess-adapt --prepare
just chess-adapt --enrich
just chess-adapt --qlora
just chess-adapt --push
```

Enrichment writes one atomic checkpoint after every provider call. A rerun
skips successes and retries failed or missing games. It stops after three
consecutive failures instead of spending the night proving that the Wi-Fi is
still down.

For a two-call smoke test before the full run:

```bash
just chess-adapt --prepare --limit 8
just chess-adapt --enrich --enrich-limit 2
```

`just chess-adapt --help` lists the filters, training settings, output paths,
private-repository switch, and overwrite guard.

Publishing is gated on held-out validation. The default requires a legal move
rate of at least 0.5; a lower or unavailable result leaves the adapter on disk
and refuses the upload. `--min-legal-rate` is visible so changing the standard
is an explicit decision rather than a hidden retry.

## Inputs

The source is `Lichess/standard-chess-games`, revision
`de4e636eddf568a9394cc01fb0b9e1da04a6babf`, file
`data/year=2013/month=01/train-00000-of-00001.parquet`. That partition is 37
MB and contains 121,332 games. The pipeline never approaches the full 4.94 TB
corpus.

The default filter selects 64 games that:

- end in a legal checkmate rather than resignation or time forfeit;
- finish within 60 plies;
- have at most three captures by the winner.

Player names are dropped. The source URL, result, ratings, SAN and UCI moves,
capture counts, final FEN, partition, revision, and selection settings remain.

Each selected game produces winner-side move examples. A successful Luna call
adds one separate real-world mapping example. Train, validation, and test
splits are assigned by game, so the same game never appears on both sides of
the evaluation.

The mapping prompt assigns a deterministic domain cue to each game. The cues
rotate through work, medicine, events, kitchens, transport, construction,
performance, science, negotiation, education, production, and sport. This
prevents sixty-four otherwise independent calls from all collapsing into the
same guards-in-a-warehouse scene.

## Credentials

Hugging Face is already authenticated locally as `ramonpzg`. The account must
also have accepted access to
`google/gemma-4-E2B-it-qat-q4_0-unquantized`.
The run pins model revision `6befbaca7398925921802abd1f277b495b78b738`;
the manifest records it again beside the adapter.

Publishing uses `HF_ACCESS_TOKEN` when it is set, otherwise the normal
Hugging Face authentication chain applies. The token needs model-repository
write permission; inference-endpoint permission alone cannot create the
adapter repository.

Luna uses the existing Chat Completions profile:

```bash
export VIDEO_PROMPT_MODEL=gpt-5.6-luna
export VIDEO_PROMPT_BASE_URL=https://api.openai.com/v1
export VIDEO_PROMPT_API_KEY=...
```

Each `VIDEO_PROMPT_*` value falls back to its `OPENAI_*` equivalent. The same
bounded retry and request-id diagnostics as the workshop backend apply.

## Training methods

QLoRA is the local default. It loads the official unquantized QAT checkpoint
through Unsloth in 4-bit, skips the image and audio towers for this text-only
run, adapts language, attention, and MLP layers, uses batch size 1 with
gradient accumulation, and applies the Gemma 4 chat template supplied by the
tokenizer. It does not hand-write Gemma special tokens.

The bf16 LoRA path is present for a larger machine:

```bash
just chess-adapt --lora --push
```

It refuses GPUs below 16 GiB before loading the model. The override is named
`--force-vram` and does exactly what its name says: it removes the check, not
the memory requirement.

Stop `just start-gemma` before either training method. The preflight checks
free as well as total VRAM and refuses to load while llama.cpp or another GPU
job occupies the memory the trainer needs.

The official DeepMind `gemma` package remains the direct JAX reference for the
notebook's low-level explanation. The overnight artifact uses one trainer,
Unsloth, rather than maintaining a second implementation of the same run.

## Outputs

Generated files are ignored by git:

```text
data/processed/text/lichess-low-capture/
  games.jsonl
  enrichments.jsonl
  manifest.json
  sft_train.jsonl
  sft_validation.jsonl
  sft_test.jsonl

artifacts/generated/chess-adapt/{qlora,lora}/
  adapter/
  work/
```

The uploaded model repository contains the PEFT adapter, tokenizer/processor,
model card, and `run_manifest.json`. The manifest records the base model,
dataset hash, exact settings, GPU, package versions, git commit, training
metrics, and raw held-out replies. It is not a merged model or a GGUF. Merging
and conversion are separate deployment work because they create another
multi-GB artifact and are not required to preserve or inspect the adapter.

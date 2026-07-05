/** Pure descriptions of the starter content seeded onto each tldraw page. */

export interface SeedNote {
  kind: "note";
  text: string;
  x: number;
  y: number;
  color?: string;
}

export interface SeedHeading {
  kind: "heading";
  text: string;
  x: number;
  y: number;
}

export type SeedShape = SeedHeading | SeedNote;

const ROW_Y = 260;
const NOTE_GAP = 260;

function noteRow(texts: string[], y = ROW_Y, color?: string): SeedNote[] {
  return texts.map((text, index) => ({
    kind: "note",
    text,
    x: index * NOTE_GAP,
    y,
    color,
  }));
}

const SEEDS_BY_SLUG: Record<string, SeedShape[]> = {
  presentation: [
    { kind: "heading", text: "Same Recipe, Different Results", x: 0, y: 0 },
    {
      kind: "heading",
      text: "Fine-tuning models across modalities. One chess domain, four modalities.",
      x: 0,
      y: 90,
    },
    ...noteRow(
      [
        "1. Text\nTeach a model to play",
        "2. Image\nTeach a model to paint pieces",
        "3. Audio\nTeach a model to voice the board",
        "4. Video\nTeach a model to render moments",
      ],
      260,
      "blue",
    ),
    ...noteRow(
      [
        "Enter your name",
        "Join your workspace",
        "Move pieces, watch the dataset build",
        "Run a job, check the evals",
      ],
      560,
      "light-green",
    ),
  ],
  "chess-machine": [
    { kind: "heading", text: "Building a Chess Machine", x: 0, y: 0 },
    {
      kind: "heading",
      text: "Text fine-tuning. SFT teaches good answers, RL teaches good actions.",
      x: 0,
      y: 90,
    },
    ...noteRow(["Prompt template", "Chess dataset", "SFT", "LoRA / QLoRA"], 260, "violet"),
    ...noteRow(["RL environment", "Stockfish", "Legality checking", "Evals"], 560, "orange"),
  ],
  "painting-pieces": [
    { kind: "heading", text: "Painting Our Pieces", x: 0, y: 0 },
    { kind: "heading", text: "Image fine-tuning. Chess piece style adaptation.", x: 0, y: 90 },
    ...noteRow(
      ["Image-caption pairs", "Trigger words", "Aspect ratios", "Captions"],
      260,
      "yellow",
    ),
    ...noteRow(["Image evals"], 560, "orange"),
  ],
  "board-sound": [
    { kind: "heading", text: "Giving the Board Sound", x: 0, y: 0 },
    { kind: "heading", text: "Audio fine-tuning. Chess sound effects.", x: 0, y: 90 },
    ...noteRow(["Audio-caption pairs", "Spectrograms", "Audio latents"], 260, "light-blue"),
    ...noteRow(["Audio evals"], 560, "orange"),
  ],
  "real-world-video": [
    { kind: "heading", text: "Video of the Real-World Use Case", x: 0, y: 0 },
    {
      kind: "heading",
      text: "Video fine-tuning. Short chess moments and real-world analogy scenes.",
      x: 0,
      y: 90,
    },
    ...noteRow(["Video-caption pairs", "Frame sampling", "Temporal consistency"], 260, "grey"),
    ...noteRow(["Video evals"], 560, "orange"),
  ],
};

export function getPageSeedShapes(slug: string): SeedShape[] {
  const seeds = SEEDS_BY_SLUG[slug];
  if (!seeds) throw new Error(`no seed content for page slug: ${slug}`);
  return seeds;
}

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

/**
 * A slide for the presenter to fill in. Rendered as a tldraw frame with
 * one prompt note inside, so the deck outline ships with the app and the
 * content gets authored on the canvas.
 */
export interface SeedFrame {
  kind: "frame";
  name: string;
  x: number;
  y: number;
  w: number;
  h: number;
  prompt: string;
}

export type SeedShape = SeedHeading | SeedNote | SeedFrame;

const SLIDE_W = 1600;
const SLIDE_H = 900;
const SLIDE_GAP = 200;
const SLIDE_ROW_Y = 1400;

function slideRow(slides: { name: string; prompt: string }[]): SeedFrame[] {
  return slides.map((slide, index) => ({
    kind: "frame",
    name: slide.name,
    x: index * (SLIDE_W + SLIDE_GAP),
    y: SLIDE_ROW_Y,
    w: SLIDE_W,
    h: SLIDE_H,
    prompt: slide.prompt,
  }));
}

const EXPLAINER_W = 1200;
const EXPLAINER_H = 650;
// To the right of the seeded note rows (which end near x=1040) and above
// the workspace grid (y=1500) and the modality panel (x<900 at y=1200),
// so explainers can never collide with generated shapes.
const EXPLAINER_X = 1400;
const EXPLAINER_Y = 80;

function explainerRow(slides: { name: string; prompt: string }[]): SeedFrame[] {
  return slides.map((slide, index) => ({
    kind: "frame",
    name: slide.name,
    x: EXPLAINER_X + index * (EXPLAINER_W + 120),
    y: EXPLAINER_Y,
    w: EXPLAINER_W,
    h: EXPLAINER_H,
    prompt: slide.prompt,
  }));
}

const PRESENTATION_SLIDES = slideRow([
  {
    name: "Slide 01 Title",
    prompt:
      "Same Recipe, Different Results.\nFine-tuning across text, image, audio, video.\nOne domain: chess.",
  },
  {
    name: "Slide 02 The chess story",
    prompt:
      "Played as a kid. Duolingo chess pathway in April.\n2 matches a day, then 30, then 50.\nOver 1000 matches. Elo past 1000.",
  },
  {
    name: "Slide 03 Elo, briefly",
    prompt: "What elo measures.\nWhy a 200 point gap matters.\nWhere 1000 sits.",
  },
  {
    name: "Slide 04 Rules refresher",
    prompt:
      "The board, the pieces, the goal.\nQueen's Gambit check: not seen it? Leave, watch it, come back.",
  },
  {
    name: "Slide 05 Chess today",
    prompt:
      "AI beat grandmasters years ago. Chess is more popular than ever.\nTournaments, big and small. What a pro earns.",
  },
  {
    name: "Slide 06 Fine-tuning is moulding intelligence",
    prompt:
      "The stages that got us to transformers and diffusion.\nWhy adapt a model instead of training one.",
  },
  {
    name: "Slide 07 The plan",
    prompt:
      "Four modalities, one recipe.\nText is the deep tutorial. Image, audio, video run faster.",
  },
  {
    name: "Slide 08 How to follow along",
    prompt:
      "Open the app. Enter your name.\nMove pieces, watch the dataset build.\nRun a job, check the evals.",
  },
  {
    name: "Slide 09 Your personalised instructor",
    prompt:
      "The point of all this: your own instructor.\nMine: win while capturing as few pieces as possible.",
  },
  {
    name: "Slide 10 Closing thoughts",
    prompt:
      "Training is expensive. Open models match closed ones from two years ago.\nThe barrier keeps dropping: microchat trains a GPT in a few hundred lines.\nMerging combines fine-tunes without retraining. Know when it wrecks quality.\nSpecialisation may soon matter more than a ten point benchmark gap.",
  },
  {
    name: "Slide 11 Resources",
    prompt: "Repo, datasets, models, further reading.\nFill before the session.",
  },
]);

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
    {
      kind: "heading",
      text: "Slides. Fill each frame, use Prev / Next to present.",
      x: 0,
      y: SLIDE_ROW_Y - 120,
    },
    ...PRESENTATION_SLIDES,
  ],
  "chess-machine": [
    { kind: "heading", text: "Building a Chess Machine", x: 0, y: 0 },
    {
      kind: "heading",
      text: "Text fine-tuning. SFT teaches good answers, RL teaches good actions.",
      x: 0,
      y: 90,
    },
    {
      kind: "note",
      text: "Play first. Your moves become the dataset next to your board.",
      x: 880,
      y: 0,
      color: "light-green",
    },
    ...noteRow(["Prompt template", "Chess dataset", "SFT", "LoRA / QLoRA"], 260, "violet"),
    ...noteRow(["RL environment", "Stockfish", "Legality checking", "Evals"], 560, "orange"),
    ...noteRow(
      [
        "Real-world mapping\nEach game relates to a scenario at work, home, sports",
        "Training ladder\nUI, API, config, code, JAX",
        "One player model\nor player plus analyst",
        "Hardware\nwhich GPU, from where",
      ],
      860,
      "light-blue",
    ),
    ...explainerRow([
      {
        name: "Explainer 01 From moves to a model",
        prompt:
          "Play a game. Every move becomes rows.\nExport the rows to a file.\nPoint the trainer at the file. That is the whole pipeline.",
      },
      {
        name: "Explainer 02 SFT vs RL",
        prompt:
          "SFT: show the model good answers.\nRL: let the model act, price every action.\nChess prices actions for free: legal +1, check +2, mate +10, illegal -1.",
      },
    ]),
  ],
  "painting-pieces": [
    { kind: "heading", text: "Painting Our Pieces", x: 0, y: 0 },
    { kind: "heading", text: "Image fine-tuning. Chess piece style adaptation.", x: 0, y: 90 },
    {
      kind: "note",
      text: "Exercise: draw your favourite piece with the draw tool. The drawings become the training set.",
      x: 880,
      y: 0,
      color: "light-green",
    },
    ...noteRow(
      ["Image-caption pairs", "Trigger words", "Aspect ratios", "Captions"],
      260,
      "yellow",
    ),
    ...noteRow(
      [
        "Diffusion vs transformers\nand text diffusion transformers",
        "Providers rewrite\nyour prompts before generation",
        "Approaches\ntext to image, image to image,\ntext to svg, editing, layering",
        "Code ladder\nUI, stablediffusion.cpp, diffusers",
      ],
      560,
      "yellow",
    ),
    ...noteRow(["Image evals"], 860, "orange"),
    ...explainerRow([
      {
        name: "Explainer 01 Diffusion in one picture",
        prompt:
          "Noise in, image out, guided by your caption.\nFine-tuning teaches the guide new words: a trigger word becomes a style.",
      },
      {
        name: "Explainer 02 Data prep is the whole game",
        prompt:
          "Captions, trigger words, aspect ratios, composition.\nImage adaptation is far more sensitive to dataset size than text.",
      },
    ]),
  ],
  "board-sound": [
    { kind: "heading", text: "Giving the Board Sound", x: 0, y: 0 },
    { kind: "heading", text: "Audio fine-tuning. Chess sound effects.", x: 0, y: 90 },
    ...noteRow(["Audio-caption pairs", "Spectrograms", "Audio latents"], 260, "light-blue"),
    ...noteRow(
      [
        "Capture sounds\nand an illegal move sound",
        "Music that intensifies\nas the game sharpens",
        "The narrator\nlet's get ready to rumble",
        "Sound as image\nspectrograms make audio visual",
      ],
      560,
      "light-blue",
    ),
    ...noteRow(["Audio evals"], 860, "orange"),
    ...explainerRow([
      {
        name: "Explainer 01 Sound as image",
        prompt:
          "Sound is vibration. Audio is its recording.\nA spectrogram turns the recording into a picture, and pictures we know how to model.",
      },
      {
        name: "Explainer 02 Tokens vs diffusion for audio",
        prompt:
          "MusicGen predicts audio tokens like an LLM predicts words.\nStable Audio denoises like an image model. Same recipe, different substrate.",
      },
    ]),
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
    ...noteRow(
      [
        "The 100 scenario prompts\nfrom the text page",
        "Generate 10 to 15 second clips\nwith top video models",
        "Fine-tune a recent LTX model\nsame recipe, heavier compute",
        "Compute escalates\nfaster than you expect",
      ],
      560,
      "grey",
    ),
    ...noteRow(["Video evals"], 860, "orange"),
    ...explainerRow([
      {
        name: "Explainer 01 Why video is hard",
        prompt:
          "Every frame must agree with the last one.\nTemporal consistency is the failure mode; compute escalates faster than you expect.",
      },
      {
        name: "Explainer 02 From prompts to LTX",
        prompt:
          "Take the 100 scenario prompts from the text page.\nGenerate short clips with a top model. Fine-tune LTX on the result.",
      },
    ]),
  ],
};

export function getPageSeedShapes(slug: string): SeedShape[] {
  const seeds = SEEDS_BY_SLUG[slug];
  if (!seeds) throw new Error(`no seed content for page slug: ${slug}`);
  return seeds;
}

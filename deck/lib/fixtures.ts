/** Fixed fixtures and placeholders for deck evidence.
 *
 * The parallel-stage rule: do not invent interfaces for phase 34 data
 * and do not invent measured values. Structure is real, values are
 * explicit placeholders. `PENDING` cells render as an en-dash-free
 * "--" on the slide; the provenance line states what is missing.
 */

export interface CompareMetric {
  name: string;
  base: string;
  adapted: string;
  /** "good" | "bad" | "none": direction of the change once measured. */
  delta: "good" | "bad" | "none";
}

export interface CompareFixture {
  task: string;
  input: string;
  baseLabel: string;
  adaptedLabel: string;
  baseOutput: string;
  adaptedOutput: string;
  metrics: CompareMetric[];
  regression: string;
  provenance: string;
}

/** Authored replay from phase 34's frozen text suite. No model was
 * trained and no provider produced these replies. The component says
 * so on screen; this fixture demonstrates the evaluation contract. */
export const TEXT_COMPARE_FIXTURE: CompareFixture = {
  task: "Legal move as JSON, frozen eval suite",
  input: "rn1qkb1r/ppp2ppp/5n2/4p3/2B1P3/5Q2/PPP2PPP/RNB1K2R w KQkq - 2 7",
  baseLabel: "BASE",
  adaptedLabel: "ADAPTED",
  baseOutput: '{"move": "c4f7"',
  adaptedOutput: '{"move": "b1c3"}',
  metrics: [
    { name: "model_legal_move_rate", base: "7/12", adapted: "12/12", delta: "good" },
    { name: "valid_json_rate", base: "10/12", adapted: "12/12", delta: "good" },
    { name: "explanation_rate", base: "8/12", adapted: "0/12", delta: "bad" },
  ],
  regression: "The scripted adapted replies omit explanations: 8/12 to 0/12.",
  provenance: "SCRIPTED REPLAY | sft-v2 | suite a274c01d640a346e | no model trained",
};

/** One deployment path's measured facts. "Self-hosted" covers both a
 * presenter laptop and rented GPU hardware you control; PLAN_V2 asks
 * for image and video on "local or rented hardware", so the path
 * label is about ownership, not physical location. */
export interface CostPath {
  /** The model, checkpoint, or provider behind this path, with its
   * source and access date once checked. "Self-hosted" versus "api"
   * is not enough when real values arrive. */
  identity: string;
  /** The quality result specific to this modality: legal+JSON rate for
   * text, identity/style for image, adherence/clipping for audio,
   * case adherence/continuity for video. Free text on purpose; the
   * four modalities do not share one metric shape. */
  outcome: string;
  /** Latency for text/audio, generation time for image/video. */
  latency: string;
  /** Marginal cost for one more request on this path. */
  perRequestCost: string;
  /** Whether this path reaches the stated quality threshold. */
  thresholdMet: string;
}

/** The self-hosted path additionally owns its hardware facts; the API
 * path's hardware is the provider's and has none. */
export interface SelfHostedPath extends CostPath {
  device: string;
  /** Training or rental cost, stated with its amortisation basis. */
  setupCost: string;
}

export interface CostRow {
  modality: string;
  task: string;
  target: string;
  /** The request-volume assumption the amortisation uses; shared by
   * both paths, since the comparison holds volume constant. */
  volume: string;
  selfHosted: SelfHostedPath;
  api: CostPath;
}

/** Rate cards checked 2026-07-22. Derived costs use the workload and
 * runtime assumptions printed in each row. Quality stays unclaimed unless
 * it was measured on an actual artifact. */
export const COST_SOURCES =
  "Rates, 2026-07-22: OpenRouter Luna $1/$6 per 1M; fal FLUX.2 LoRA $0.021/MP, LTX-2 ~$0.202/5s 720p; Eleven Music $0.15/min; Runpod 4090 $0.69/h, H100 $2.89/h. Totals use the volumes shown.";

export const COST_ROWS: CostRow[] = [
  {
    modality: "Text",
    task: "legal-move JSON",
    target: "valid JSON + legal move",
    volume: "1,000 move replies",
    selfHosted: {
      identity: "Gemma 4 E2B + chess QLoRA",
      outcome: "8/8 JSON; 8/8 legal (held out)",
      latency: "not timed separately",
      perRequestCost: "$0 usage bill",
      thresholdMet: "yes, 8/8 held out",
      device: "RTX 2000 Ada, 8GB",
      setupCost: "4m03s training",
    },
    api: {
      identity: "gpt-5.6-luna via OpenRouter",
      outcome: "quality not run on same suite",
      latency: "~1.66s first token",
      perRequestCost: "$0.00058; $0.58/1k",
      thresholdMet: "not measured",
    },
  },
  {
    modality: "Image",
    task: "themed 1 MP image",
    target: "identity + style adherence",
    volume: "100 x 1 MP images",
    selfHosted: {
      identity: "FLUX.2 Klein 4B + LoRA",
      outcome: "~$0.19 compute for 100",
      latency: "10s assumption",
      perRequestCost: "~$0.0019 at 10s",
      thresholdMet: "not measured",
      device: "RTX 4090, 24GB",
      setupCost: "$0.69/GPU-hour",
    },
    api: {
      identity: "FLUX.2 LoRA on fal.ai",
      outcome: "$2.10 for 100 x 1 MP",
      latency: "provider not stated",
      perRequestCost: "$0.021/MP",
      thresholdMet: "not measured",
    },
  },
  {
    modality: "Audio",
    task: "30-second music clip",
    target: "prompt fit + no clipping",
    volume: "50 x 30s clips",
    selfHosted: {
      identity: "musicgen-small, local",
      outcome: "local clip approved by Ramon",
      latency: "fast; not timed",
      perRequestCost: "$0 usage bill",
      thresholdMet: "yes, human review",
      device: "RTX 2000 Ada, 8GB",
      setupCost: "$0, weights cached",
    },
    api: {
      identity: "Eleven Music API",
      outcome: "$3.75 for 25 minutes",
      latency: "provider not stated",
      perRequestCost: "$0.075 per 30s",
      thresholdMet: "not measured",
    },
  },
  {
    modality: "Video",
    task: "5-second 720p scene",
    target: "case adherence + continuity",
    volume: "20 x 5s clips",
    selfHosted: {
      identity: "LTX-2 19B, self-hosted",
      outcome: "~$0.59 compute for 20",
      latency: "~37s at 30 steps",
      perRequestCost: "~$0.029 at 30 steps",
      thresholdMet: "not measured",
      device: "H100 80GB",
      setupCost: "$2.89/GPU-hour",
    },
    api: {
      identity: "LTX-2-19B on fal.ai",
      outcome: "~$4.03 for 20 clips",
      latency: "provider not stated",
      perRequestCost: "~$0.202/5s 720p",
      thresholdMet: "not measured",
    },
  },
];

export interface AbPair {
  modality: string;
  question: string;
  aFile: string;
  bFile: string;
  ratio: string;
  kind: "text" | "image" | "audio" | "video";
  expected: string;
}

/** The four A/B slides. Only actual adapted/reference pairs may fill
 * these; provenance travels with the files when they land. */
export const AB_PAIRS: AbPair[] = [
  {
    modality: "text",
    question: "Two move choices for the same position. Which model was adapted?",
    aFile: "ab-text-a.png",
    bFile: "ab-text-b.png",
    ratio: "16/10",
    kind: "image",
    expected: "rendered model reply, matched input",
  },
  {
    modality: "image",
    question: "Same prompt, two sets of pieces. Which came from the adapter?",
    aFile: "ab-image-a.png",
    bFile: "ab-image-b.png",
    ratio: "1/1",
    kind: "image",
    expected: "generated board image",
  },
  {
    modality: "audio",
    question: "Two clips for the same text. Which model was adapted?",
    aFile: "ab-audio-a.wav",
    bFile: "ab-audio-b.wav",
    ratio: "16/3",
    kind: "audio",
    expected: "generated audio clip",
  },
  {
    modality: "video",
    question: "Same scene prompt, two clips. Which one was adapted?",
    aFile: "ab-video-a.mp4",
    bFile: "ab-video-b.mp4",
    ratio: "16/9",
    kind: "video",
    expected: "generated scene clip, no chess objects",
  },
];

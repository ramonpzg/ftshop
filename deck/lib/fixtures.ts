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

export interface CostPath {
  identity: string;
  cost: string;
  /** The arithmetic or omission that makes the total interpretable. */
  basis: string;
}

export interface CostRow {
  modality: string;
  batch: string;
  selfHosted: CostPath;
  api: CostPath;
  takeaway: string;
  source: string;
}

export const COST_ROWS: CostRow[] = [
  {
    modality: "Text",
    batch: "1,000 short chess replies",
    selfHosted: {
      identity: "Gemma on this laptop",
      cost: "$0 API bill",
      basis: "power, hardware, and setup excluded",
    },
    api: {
      identity: "Luna API",
      cost: "about $0.58",
      basis: "400 input + 30 output tokens each",
    },
    takeaway: "Text API usage is already cheap. Cost alone is a weak reason to adapt.",
    source: "OpenRouter rate card, checked 22 July 2026.",
  },
  {
    modality: "Image",
    batch: "100 one-megapixel images",
    selfHosted: {
      identity: "FLUX Klein on a rented 4090",
      cost: "about $0.19",
      basis: "assumes 10 seconds each at $0.69/hour",
    },
    api: {
      identity: "FLUX.2 LoRA on fal.ai",
      cost: "$2.10",
      basis: "100 images x $0.021/megapixel",
    },
    takeaway: "The usage gap is real. We have not shown equal output quality.",
    source: "fal and Runpod rate cards; local runtime is an assumption.",
  },
  {
    modality: "Audio",
    batch: "50 thirty-second music clips",
    selfHosted: {
      identity: "MusicGen on this laptop",
      cost: "$0 API bill",
      basis: "power, hardware, and setup excluded",
    },
    api: {
      identity: "Eleven Music API",
      cost: "$3.75",
      basis: "25 output minutes x $0.15/minute",
    },
    takeaway: "We heard the local result. We did not compare it with Eleven Music.",
    source: "ElevenLabs API pricing, checked 22 July 2026.",
  },
  {
    modality: "Video",
    batch: "20 five-second 720p clips",
    selfHosted: {
      identity: "LTX on a rented H100",
      cost: "about $0.59",
      basis: "30-step estimate at $2.89/hour",
    },
    api: {
      identity: "LTX-2-19B on fal.ai",
      cost: "about $4.03",
      basis: "20 clips x fal's $0.2016 example",
    },
    takeaway: "The API buys simplicity. The rental estimate excludes setup.",
    source: "fal, Runpod, and LTX rate cards and timing report.",
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

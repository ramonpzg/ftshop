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

const PENDING_FACTS = {
  outcome: "PENDING",
  latency: "[SOURCE, DATE]",
  perRequestCost: "[SOURCE, DATE]",
  thresholdMet: "PENDING",
};

const PENDING_HARDWARE = {
  device: "[SOURCE, DATE]",
  setupCost: "[SOURCE, DATE]",
};

/** Slide 22 economics rows. Model identities use the accepted names
 * where they exist; everything measured is a placeholder until checked
 * close to the session, and every final value gets a source and access
 * date. Threshold attainment is tracked per path, since the point of
 * the slide is that the two paths can disagree on whether the target
 * is met. */
export const COST_ROWS: CostRow[] = [
  {
    modality: "Text",
    task: "legal-move JSON",
    target: "legal + JSON rate at threshold",
    volume: "PENDING",
    selfHosted: {
      identity: "gemma-4-2b-local, adapted ckpt PENDING",
      ...PENDING_FACTS,
      ...PENDING_HARDWARE,
    },
    api: { identity: "gpt-5.6-luna [SOURCE, DATE]", ...PENDING_FACTS },
  },
  {
    modality: "Image",
    task: "themed set, same prompt",
    target: "identity + style adherence",
    volume: "PENDING",
    selfHosted: {
      identity: "FLUX, style adapter PENDING",
      ...PENDING_FACTS,
      ...PENDING_HARDWARE,
    },
    api: { identity: "configured API image path [SOURCE, DATE]", ...PENDING_FACTS },
  },
  {
    modality: "Audio",
    task: "same prompt and duration",
    target: "adherence, no clipping",
    volume: "PENDING",
    selfHosted: {
      identity: "MusicGen, adapter PENDING",
      ...PENDING_FACTS,
      ...PENDING_HARDWARE,
    },
    api: { identity: "configured API audio path [SOURCE, DATE]", ...PENDING_FACTS },
  },
  {
    modality: "Video",
    task: "saved Luna scene prompt",
    target: "case adherence + continuity",
    volume: "PENDING",
    selfHosted: {
      identity: "LTX, rented GPU, ckpt PENDING",
      ...PENDING_FACTS,
      ...PENDING_HARDWARE,
    },
    api: { identity: "configured API video path [SOURCE, DATE]", ...PENDING_FACTS },
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

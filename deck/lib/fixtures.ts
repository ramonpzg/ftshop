/** Fixed placeholder fixtures for slides whose data arrives with the
 * accepted phase 34 result or from Ramon.
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

/** Base versus adapted on the frozen text eval suite. Values land at
 * phase 34 integration. The metric set and the trade direction follow
 * the phase 34 contract: legality and JSON validity improve, the
 * adapted checkpoint deliberately loses explanations. */
export const TEXT_COMPARE_PLACEHOLDER: CompareFixture = {
  task: "Legal move as JSON, frozen eval suite",
  input: "PLACEHOLDER: one FEN + prompt from the frozen suite",
  baseLabel: "BASE",
  adaptedLabel: "ADAPTED",
  baseOutput: "--",
  adaptedOutput: "--",
  metrics: [
    { name: "model_legal_move_rate", base: "--", adapted: "--", delta: "good" },
    { name: "valid_json_rate", base: "--", adapted: "--", delta: "good" },
    { name: "explanation_rate", base: "--", adapted: "--", delta: "bad" },
  ],
  regression: "Explanation rate drops on the adapted checkpoint, by design.",
  provenance: "PENDING PHASE 34 INTEGRATION",
};

/** One deployment path's measured facts. "Self-hosted" covers both a
 * presenter laptop and rented GPU hardware you control; PLAN_V2 asks
 * for image and video on "local or rented hardware", so the path
 * label is about ownership, not physical location. */
export interface CostPath {
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

export interface CostRow {
  modality: string;
  task: string;
  target: string;
  /** Self-hosted path only; the API path's hardware is the provider's. */
  device: string;
  /** Training or rental cost, stated with its amortisation basis. */
  setupCost: string;
  /** The request-volume assumption the amortisation uses. */
  volume: string;
  selfHosted: CostPath;
  api: CostPath;
}

const PENDING_PATH: CostPath = {
  outcome: "PENDING",
  latency: "[SOURCE, DATE]",
  perRequestCost: "[SOURCE, DATE]",
  thresholdMet: "PENDING",
};

/** Slide 22 economics rows. Every value is a placeholder until checked
 * close to the session; sources and access dates required. Threshold
 * attainment is tracked per path, since the point of the slide is
 * that the two paths can disagree on whether the target is met. */
export const COST_ROWS: CostRow[] = [
  {
    modality: "Text",
    task: "legal-move JSON",
    target: "legal + JSON rate at threshold",
    device: "[SOURCE, DATE]",
    setupCost: "[SOURCE, DATE]",
    volume: "PENDING",
    selfHosted: { ...PENDING_PATH },
    api: { ...PENDING_PATH },
  },
  {
    modality: "Image",
    task: "themed set, same prompt",
    target: "identity + style adherence",
    device: "[SOURCE, DATE]",
    setupCost: "[SOURCE, DATE]",
    volume: "PENDING",
    selfHosted: { ...PENDING_PATH },
    api: { ...PENDING_PATH },
  },
  {
    modality: "Audio",
    task: "same prompt and duration",
    target: "adherence, no clipping",
    device: "[SOURCE, DATE]",
    setupCost: "[SOURCE, DATE]",
    volume: "PENDING",
    selfHosted: { ...PENDING_PATH },
    api: { ...PENDING_PATH },
  },
  {
    modality: "Video",
    task: "saved Luna scene prompt",
    target: "case adherence + continuity",
    device: "[SOURCE, DATE]",
    setupCost: "[SOURCE, DATE]",
    volume: "PENDING",
    selfHosted: { ...PENDING_PATH },
    api: { ...PENDING_PATH },
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

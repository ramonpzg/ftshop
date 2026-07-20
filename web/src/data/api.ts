/** Thin fetch wrapper for the backend. No business logic here. */

const BASE_URL = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** FastAPI's error body is `{"detail": ...}`. `detail` is usually a
 * plain string, but a few 409s (turn-ownership vs. clock-expiry
 * conflicts) send `{code, message}` instead, so a client can branch on
 * `code` rather than pattern-matching English prose. */
type ErrorDetail = string | { code?: string; message?: string };

function parsedErrorDetail(error: unknown): ErrorDetail | null {
  if (!(error instanceof ApiError)) return null;
  try {
    return JSON.parse(error.message).detail ?? null;
  } catch {
    return null;
  }
}

/** The human sentence inside a FastAPI error body, for showing to the
 * user instead of a silent failure. */
export function apiErrorDetail(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  const detail = parsedErrorDetail(error);
  if (typeof detail === "string") return detail;
  if (detail && typeof detail.message === "string") return detail.message;
  return error.message;
}

/** The stable machine code on a structured error body (see
 * ErrorDetail), or null when this error doesn't carry one -- either
 * because it never had structured detail, or detail is a plain
 * string. Callers branch on this instead of substring-matching
 * `apiErrorDetail`'s prose, which a copy edit could change without
 * anyone noticing the branch it used to control. */
export function apiErrorCode(error: unknown): string | null {
  const detail = parsedErrorDetail(error);
  if (detail && typeof detail === "object" && typeof detail.code === "string") {
    return detail.code;
  }
  return null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  return response.json() as Promise<T>;
}

export interface HealthStatus {
  status: string;
}

export function fetchHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

export interface RoomHealth {
  status: string;
  /** The sync room's persistence state toward the backend disk:
   * idle (nothing to save yet), saving, saved, or error (retrying). */
  persist: "idle" | "saving" | "saved" | "error";
  sessions: number;
}

/** The sync server's health endpoint. Not under /api: the room is its
 * own process, reached through the dev server's /sync proxy. */
export async function fetchRoomHealth(): Promise<RoomHealth> {
  const response = await fetch("/sync/health");
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  return response.json() as Promise<RoomHealth>;
}

export interface User {
  id: string;
  name: string;
  created_at: string;
}

export function createUser(name: string): Promise<User> {
  return request<User>("/users", { method: "POST", body: JSON.stringify({ name }) });
}

export interface Workspace {
  id: string;
  user_id: string;
  page_id: string;
  shape_id: string;
  position_index: number;
  selected_snippet_id: string | null;
  board_fen: string;
}

export interface WorkspaceWithDetails extends Workspace {
  user_name: string;
  page_slug: string;
  page_title: string;
}

export function createOrGetWorkspace(userId: string, pageSlug: string): Promise<Workspace> {
  return request<Workspace>("/workspaces", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, page_slug: pageSlug }),
  });
}

export function fetchWorkspaces(): Promise<WorkspaceWithDetails[]> {
  return request<WorkspaceWithDetails[]>("/workspaces");
}

export interface Move {
  id: string;
  workspace_id: string;
  ply: number;
  uci: string;
  san: string | null;
  fen_before: string;
  fen_after: string;
  is_legal: boolean;
  is_check: boolean;
  is_checkmate: boolean;
  reward: number;
  /** Who attempted it: participant, model, fallback, or unknown for
   * rows from before provenance existed. */
  actor: string;
  /** The model that produced it, when an actor is model or fallback. */
  model: string | null;
  created_at: string;
}

export interface DatasetRow {
  id: string;
  workspace_id: string;
  move_id: string | null;
  shape: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface MoveResponse {
  move: Move;
  dataset_rows: DatasetRow[];
  /** Set when this move ended a timed game: "win", "loss", "draw". */
  game_result: string | null;
}

export function makeMove(workspaceId: string, uci: string): Promise<MoveResponse> {
  return request<MoveResponse>(`/workspaces/${workspaceId}/moves`, {
    method: "POST",
    body: JSON.stringify({ uci }),
  });
}

export interface WorkspaceState {
  workspace: Workspace;
  moves: Move[];
  dataset_rows: DatasetRow[];
}

export interface ModelOption {
  id: string;
  label: string;
  available: boolean;
}

export interface ModalityGenerationOptions {
  configured: boolean;
  models: ModelOption[];
}

export interface GenerationOptions {
  image: ModalityGenerationOptions;
  video: ModalityGenerationOptions;
  audio: ModalityGenerationOptions;
}

export function fetchGenerationOptions(): Promise<GenerationOptions> {
  return request<GenerationOptions>("/generation/options");
}

export interface DatasetExport {
  file_name: string;
  row_count: number;
  url: string;
}

export function exportTextDataset(): Promise<DatasetExport> {
  return request<DatasetExport>("/datasets/text/export", { method: "POST" });
}

export interface LlmStatus {
  configured: boolean;
  model: string;
  opponent_models: string[];
}

export function fetchLlmStatus(): Promise<LlmStatus> {
  return request<LlmStatus>("/llm/status");
}

export interface ModelTurnAttempt {
  attempt_number: number;
  actor: string;
  status: string;
  parsed_move: string | null;
  is_legal: boolean | null;
  model: string | null;
  error_detail: string | null;
}

export interface ModelTurnResponse {
  /** "model_move": the model's reply was applied. "fallback_move": it
   * kept failing and the deterministic fallback moved. "unavailable":
   * transport never delivered a reply and nothing moved. "stale": the
   * position changed while a reply was in flight and nothing moved. */
  outcome: "model_move" | "fallback_move" | "unavailable" | "stale";
  move: Move | null;
  dataset_rows: DatasetRow[];
  game_result: string | null;
  attempts: ModelTurnAttempt[];
  detail: string | null;
}

export function modelMove(workspaceId: string): Promise<ModelTurnResponse> {
  return request<ModelTurnResponse>(`/workspaces/${workspaceId}/model-move`, { method: "POST" });
}

export interface Game {
  id: string;
  workspace_id: string;
  time_limit_seconds: number;
  opponent_model: string | null;
  started_at: string;
  ended_at: string | null;
  result: string | null;
  seconds_left: number;
}

export interface GameRecord {
  wins: number;
  losses: number;
  draws: number;
}

export interface FinishedGame {
  id: string;
  result: string;
  time_limit_seconds: number;
  ended_at: string;
  legal_moves: number;
}

export interface GameStatus {
  game: Game | null;
  record: GameRecord;
  board_fen: string;
  /** Finished matches, newest first. */
  history: FinishedGame[];
  /** True when this response is the first news of a timeout that
   * happened while the player was away (reload, server restart). */
  expired_while_away: boolean;
}

export function fetchGameStatus(workspaceId: string): Promise<GameStatus> {
  return request<GameStatus>(`/workspaces/${workspaceId}/game`);
}

export function startGame(
  workspaceId: string,
  timeLimitSeconds: number,
  opponentModel?: string,
): Promise<GameStatus> {
  return request<GameStatus>(`/workspaces/${workspaceId}/game/start`, {
    method: "POST",
    body: JSON.stringify({
      time_limit_seconds: timeLimitSeconds,
      opponent_model: opponentModel ?? null,
    }),
  });
}

/** Ends the running game as a loss and starts a fresh one. The Duolingo rule. */
export function startOver(workspaceId: string): Promise<GameStatus> {
  return request<GameStatus>(`/workspaces/${workspaceId}/game/start-over`, { method: "POST" });
}

/** The client clock hit zero; the server verifies before recording the loss. */
export function flagTimeout(workspaceId: string): Promise<GameStatus> {
  return request<GameStatus>(`/workspaces/${workspaceId}/game/timeout`, { method: "POST" });
}

export interface Scenario {
  id: string;
  workspace_id: string;
  game_id: string | null;
  ply: number;
  /** suggested, accepted, edited, or failed. assessPosition and
   * reviewScenario only ever resolve to a non-failed record (a failure
   * throws instead); fetchScenario can return a failed one, since
   * reload must be able to show the same recoverable failure state a
   * live attempt shows. */
  status: string;
  /** Effective text: participant-approved when reviewed, the raw
   * suggestion otherwise. Null when status is "failed". */
  assessment: string | null;
  real_world: string | null;
  video_prompt: string | null;
  suggested_assessment: string | null;
  suggested_real_world: string | null;
  suggested_video_prompt: string | null;
  model: string | null;
  provider_alias: string | null;
  prompt_version: string | null;
  /** Set when status is "failed": why the last attempt didn't produce
   * a usable scenario. */
  error_detail: string | null;
  created_at: string;
}

/** Asks for a fresh suggestion; the backend persists it with its raw
 * reply and provenance before answering. */
export function assessPosition(workspaceId: string): Promise<Scenario> {
  return request<Scenario>(`/workspaces/${workspaceId}/assess`, { method: "POST" });
}

export interface ScenarioReload {
  /** The true most recent scenario, whatever its status -- possibly a
   * failure. Never hidden: a failure is a fact about the last attempt. */
  latest: Scenario | null;
  /** The most recent scenario that actually produced a usable mapping.
   * The same row as `latest` when the last attempt succeeded, an older
   * row when it failed, or null when nothing has ever succeeded. This
   * is what a live failure leaves on screen while showing the new
   * error alongside it; reload needs both rows to restore that same
   * combination instead of only ever surfacing whichever is newest. */
  latest_success: Scenario | null;
}

/** The reload read: the latest scenario state plus the last one that
 * actually succeeded, so a failure never silently hides an earlier
 * mapping that a live failure would have kept visible. */
export function fetchScenario(workspaceId: string): Promise<ScenarioReload> {
  return request<ScenarioReload>(`/workspaces/${workspaceId}/scenario`);
}

export interface ScenarioReview {
  accept: boolean;
  assessment?: string;
  real_world?: string;
  video_prompt?: string;
}

export function reviewScenario(scenarioId: string, review: ScenarioReview): Promise<Scenario> {
  return request<Scenario>(`/scenarios/${scenarioId}/review`, {
    method: "POST",
    body: JSON.stringify(review),
  });
}

export function fetchWorkspaceState(workspaceId: string): Promise<WorkspaceState> {
  return request<WorkspaceState>(`/workspaces/${workspaceId}/state`);
}

export function selectSnippet(workspaceId: string, snippetId: string): Promise<Workspace> {
  return request<Workspace>(`/workspaces/${workspaceId}/snippet`, {
    method: "PUT",
    body: JSON.stringify({ snippet_id: snippetId }),
  });
}

export interface PresenterTargetBounds {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PresenterState {
  mode: string;
  locked: boolean;
  active_page_slug: string | null;
  focused_user_id: string | null;
  updated_at: string;
  /** Monotonic; bumped by the backend on every presenter-state change.
   * Clients order camera updates on this alone. */
  revision: number;
  target_frame_id: string | null;
  target_bounds: PresenterTargetBounds | null;
}

export interface PresenterTarget {
  pageSlug: string;
  frameId?: string;
  bounds?: PresenterTargetBounds;
}

export function fetchPresenterState(signal?: AbortSignal): Promise<PresenterState> {
  return request<PresenterState>("/presenter", { signal });
}

export function bringToPresenterView(target: PresenterTarget): Promise<PresenterState> {
  return request<PresenterState>("/presenter/bring-to-presenter-view", {
    method: "POST",
    body: JSON.stringify({
      page_slug: target.pageSlug,
      frame_id: target.frameId ?? null,
      bounds: target.bounds ?? null,
    }),
  });
}

export function sendToWorkspaces(): Promise<PresenterState> {
  return request<PresenterState>("/presenter/send-to-workspaces", { method: "POST" });
}

export function lockEditing(): Promise<PresenterState> {
  return request<PresenterState>("/presenter/lock", { method: "POST" });
}

export function unlockEditing(): Promise<PresenterState> {
  return request<PresenterState>("/presenter/unlock", { method: "POST" });
}

export interface RoomGame {
  id: string;
  workspace_id: string;
  user_name: string;
  result: string | null;
  time_limit_seconds: number;
  started_at: string;
  ended_at: string | null;
  seconds_left: number | null;
  legal_moves: number;
  dataset_rows: number;
}

export interface RoomGames {
  games: RoomGame[];
  playing: number;
  finished: number;
  total_dataset_rows: number;
}

export function fetchRoomGames(): Promise<RoomGames> {
  return request<RoomGames>("/presenter/games");
}

export function exportFullTextDataset(): Promise<DatasetExport> {
  return request<DatasetExport>("/datasets/text/export-full", { method: "POST" });
}

export interface ResetPageResponse {
  workspaces_reset: number;
}

export function resetPage(pageSlug: string): Promise<ResetPageResponse> {
  return request<ResetPageResponse>("/presenter/reset-page", {
    method: "POST",
    body: JSON.stringify({ page_slug: pageSlug }),
  });
}

export interface Artifact {
  id: string;
  job_config_id: string | null;
  modality: string;
  kind: string;
  payload: Record<string, unknown>;
  cached: boolean;
  created_at: string;
}

export interface JobConfigOut {
  id: string;
  workspace_id: string | null;
  job_type: string;
  params_json: string;
  created_at: string;
}

export interface RunJobResponse {
  job_config: JobConfigOut;
  artifact: Artifact;
}

export function runJob(
  jobType: string,
  params: Record<string, unknown> = {},
  workspaceId?: string,
  opts: { signal?: AbortSignal } = {},
): Promise<RunJobResponse> {
  return request<RunJobResponse>("/jobs", {
    method: "POST",
    body: JSON.stringify({ job_type: jobType, params, workspace_id: workspaceId ?? null }),
    signal: opts.signal,
  });
}

export function fetchArtifacts(
  opts: { modality?: string; workspaceId?: string } = {},
): Promise<Artifact[]> {
  const query = new URLSearchParams();
  if (opts.modality) query.set("modality", opts.modality);
  if (opts.workspaceId) query.set("workspace_id", opts.workspaceId);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<Artifact[]>(`/artifacts${suffix}`);
}

/** Opaque tldraw document snapshot. The backend stores it without inspecting it. */
export type CanvasSnapshot = Record<string, unknown>;

export function fetchCanvasSnapshot(): Promise<CanvasSnapshot | null> {
  return request<{ snapshot: CanvasSnapshot | null }>("/canvas").then((body) => body.snapshot);
}

export function saveCanvasSnapshot(snapshot: CanvasSnapshot): Promise<{ saved: boolean }> {
  return request<{ saved: boolean }>("/canvas", {
    method: "PUT",
    body: JSON.stringify({ snapshot }),
  });
}

export async function uploadCanvasAsset(name: string, file: File): Promise<{ name: string }> {
  const form = new FormData();
  form.append("file", file, name);
  const response = await fetch(`${BASE_URL}/canvas/assets`, { method: "POST", body: form });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  return response.json() as Promise<{ name: string }>;
}

export function canvasAssetUrl(name: string): string {
  return `${BASE_URL}/canvas/assets/${name}`;
}

export interface EvalResult {
  id: string;
  modality: string;
  metric: string;
  value: number;
  workspace_id: string | null;
  source: string;
  /** Computed rows carry sample counts and the metric definition;
   * cached rows carry the fixture's note. */
  numerator: number | null;
  denominator: number | null;
  unit: string | null;
  direction: string | null;
  definition: string | null;
  version: string | null;
  scope_json: string | null;
  note: string | null;
  /** Which model/checkpoint version this result scopes to, when
   * scoped: base and adapted results carry different values here and
   * coexist rather than overwrite each other. */
  model: string | null;
  checkpoint: string | null;
  /** Groups every metric produced by one eval job execution. */
  run_id: string | null;
  /** An audit trail back to the exact move/attempt rows counted. Not a
   * stable cross-model identity by itself -- two models produce two
   * different sets of row ids even over the identical position. */
  sample_ids: string[];
  /** The actual frozen input set: a deterministic hash of the exact
   * fens the sample was measured over. Two results with matching ids
   * were measured on the identical positions and are honestly
   * comparable; different ids mean they were not, no matter how
   * similar model/checkpoint look. */
  position_set_id: string | null;
  /** The fens themselves, in sample order. */
  positions: string[];
  created_at: string;
}

export function fetchEvals(
  opts: { modality?: string; workspaceId?: string } = {},
): Promise<EvalResult[]> {
  const query = new URLSearchParams();
  if (opts.modality) query.set("modality", opts.modality);
  if (opts.workspaceId) query.set("workspace_id", opts.workspaceId);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<EvalResult[]>(`/evals${suffix}`);
}

/** A frozen training dataset: the exact SFT rows, hashed, with the
 * eligibility and approval counts that explain what was kept out. */
export interface DatasetSnapshot {
  id: string;
  label: string;
  modality: string;
  /** 'seeded' for the reviewed reference fixture, 'frozen' for a
   * snapshot taken from the room's own play. */
  origin: string;
  schema_version: string;
  row_count: number;
  excluded_ineligible_count: number;
  source_game_count: number;
  source_workspace_count: number;
  scenario_raw_count: number;
  scenario_approved_count: number;
  content_hash: string;
  note: string | null;
  created_at: string;
  /** First rows of the frozen content; state responses only. */
  row_preview?: Array<{ prompt: string; completion: string }>;
}

export interface TrainingConfigInfo {
  config_id: string;
  label: string;
  modality: string;
  base_model: string;
  method: string;
  lora_r: number;
  lora_alpha: number;
  lora_dropout: number;
  learning_rate: number;
  epochs: number;
  batch_size: number;
  seed: number;
  output_task: string;
  target_checkpoint: string;
  serving_alias: string;
  inference_repo: string;
  config_hash: string;
  limitations: string;
}

export interface AdapterInfo {
  id: string;
  label: string;
  modality: string;
  checkpoint: string;
  base_model: string;
  method: string;
  seed: number;
  output_task: string;
  config_id: string;
  config_hash: string;
  config: Record<string, unknown>;
  dataset_snapshot_id: string;
  dataset_content_hash: string;
  runner: string;
  result_source: string;
  limitations: string;
  created_at: string;
}

export interface SuiteExample {
  example_id: string;
  fen: string;
  legal_moves: string[];
  prompt: string;
}

export interface EvalSuite {
  id: string;
  label: string;
  modality: string;
  origin: string;
  prompt_version: string;
  schema_version: string;
  example_count: number;
  content_hash: string;
  position_set_id: string;
  note: string | null;
  created_at: string;
  examples: SuiteExample[];
}

export interface BenchmarkMetricRow {
  id: string;
  modality: string;
  metric: string;
  value: number;
  workspace_id: string | null;
  source: string;
  numerator: number | null;
  denominator: number | null;
  unit: string | null;
  direction: string | null;
  definition: string | null;
  version: string | null;
  note: string | null;
  model: string | null;
  checkpoint: string | null;
  run_id: string | null;
  sample_ids: string[];
  position_set_id: string | null;
  created_at: string;
}

export interface BenchmarkRun {
  id: string;
  suite_id: string;
  suite_content_hash: string;
  prompt_version: string;
  checkpoint: string;
  model: string;
  provider_alias: string | null;
  /** 'live' or 'replayed'; the run never poses as the other. */
  source: string;
  example_count: number;
  reply_count: number;
  transport_failed_count: number;
  position_set_id: string | null;
  note: string | null;
  created_at: string;
  metrics: BenchmarkMetricRow[];
}

export interface MetricComparison {
  metric: string;
  comparable: boolean;
  reason: string | null;
  base_value: number | null;
  adapted_value: number | null;
  delta: number | null;
  verdict: "improved" | "regressed" | "unchanged" | null;
  unit: string | null;
  direction: string | null;
  base_numerator: number | null;
  base_denominator: number | null;
  adapted_numerator: number | null;
  adapted_denominator: number | null;
  definition: string | null;
  version: string | null;
  position_set_id: string | null;
}

export interface ExampleReplyView {
  status: string;
  raw_response: string | null;
  parsed_move: string | null;
  is_legal: boolean | null;
  reply_source: string;
}

export interface ExampleComparison {
  example_id: string;
  fen: string;
  prompt: string;
  base: ExampleReplyView | null;
  adapted: ExampleReplyView | null;
}

export interface AdaptationComparison {
  suite_id: string;
  suite_label: string;
  base_run: Omit<BenchmarkRun, "metrics">;
  adapted_run: Omit<BenchmarkRun, "metrics">;
  comparable: boolean;
  reasons: string[];
  metrics: MetricComparison[];
  examples: ExampleComparison[];
}

export interface AdaptationState {
  snapshots: DatasetSnapshot[];
  configs: TrainingConfigInfo[];
  adapters: AdapterInfo[];
  suites: EvalSuite[];
  runs: BenchmarkRun[];
  comparison: AdaptationComparison | null;
  live_benchmark: { available: boolean; model: string | null };
}

export function fetchAdaptationState(): Promise<AdaptationState> {
  return request<AdaptationState>("/adaptation/state");
}

export function freezeDatasetSnapshot(label?: string): Promise<DatasetSnapshot> {
  return request<DatasetSnapshot>("/adaptation/snapshots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(label ? { label } : {}),
  });
}

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

export function fetchWorkspaceState(workspaceId: string): Promise<WorkspaceState> {
  return request<WorkspaceState>(`/workspaces/${workspaceId}/state`);
}

export function selectSnippet(workspaceId: string, snippetId: string): Promise<Workspace> {
  return request<Workspace>(`/workspaces/${workspaceId}/snippet`, {
    method: "PUT",
    body: JSON.stringify({ snippet_id: snippetId }),
  });
}

export interface PresenterState {
  mode: string;
  locked: boolean;
  active_page_slug: string | null;
  focused_user_id: string | null;
  updated_at: string;
}

export function fetchPresenterState(): Promise<PresenterState> {
  return request<PresenterState>("/presenter");
}

export function bringToPresenterView(pageSlug: string): Promise<PresenterState> {
  return request<PresenterState>("/presenter/bring-to-presenter-view", {
    method: "POST",
    body: JSON.stringify({ page_slug: pageSlug }),
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
): Promise<RunJobResponse> {
  return request<RunJobResponse>("/jobs", {
    method: "POST",
    body: JSON.stringify({ job_type: jobType, params, workspace_id: workspaceId ?? null }),
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

export interface EvalResult {
  id: string;
  modality: string;
  metric: string;
  value: number;
  workspace_id: string | null;
  source: string;
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

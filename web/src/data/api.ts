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

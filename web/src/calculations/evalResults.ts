/** Pure reduction over eval results. No I/O. */

import type { EvalResult } from "../data/api";

/** Keeps only the newest row per (modality, metric, source, workspace,
 * model, checkpoint). The backend intentionally keeps every position-
 * set window a re-run ever produced (see eval_results_repo.py), so a
 * workspace that has been evaluated three times over a growing move
 * history has three real rows for the same metric with denominators
 * 1, 2, and 3. That history is worth keeping in the database; showing
 * all of it in a live panel just reads as duplicate, indistinguishable
 * rows. This is a display-only reduction -- it drops nothing from the
 * argument's source of truth, it only chooses what to render. */
export function latestEvalResultsByScope(results: EvalResult[]): EvalResult[] {
  const latestByScope = new Map<string, EvalResult>();
  for (const result of results) {
    const scopeKey = JSON.stringify([
      result.modality,
      result.metric,
      result.source,
      result.workspace_id,
      result.model,
      result.checkpoint,
    ]);
    const current = latestByScope.get(scopeKey);
    if (!current || result.created_at >= current.created_at) {
      latestByScope.set(scopeKey, result);
    }
  }
  return [...latestByScope.values()];
}

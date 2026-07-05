/** Pure ID helpers. No side effects, no I/O. */

export function generateLocalId(prefix: string): string {
  const uuid = crypto.randomUUID();
  return `${prefix}_${uuid}`;
}

export function workspaceShapeId(userId: string, pageSlug: string): string {
  return `shape:workspace-${userId}-${pageSlug}`;
}

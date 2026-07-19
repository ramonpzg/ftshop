/** The connection states the synced room can actually be in, and their
 * badge copy. Stale and conflicted states cannot occur under tldraw
 * sync's rebase model: a reconnecting client replays its offline changes
 * on top of the server document instead of overwriting it, so there is
 * nothing to show for them. */

export type RoomStatus = "connecting" | "live" | "offline" | "error";

export const ROOM_STATUS_LABELS: Record<RoomStatus, string> = {
  connecting: "Room: connecting",
  live: "Room: live",
  offline: "Room: offline, retrying",
  error: "Room: sync failed. Reload.",
};

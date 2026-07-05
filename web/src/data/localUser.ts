/** Local persistence of the joined user's identity. No server round trip. */

const STORAGE_KEY = "euro-chess-studio:current-user";

export interface LocalUser {
  id: string;
  name: string;
}

export function loadLocalUser(): LocalUser | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as LocalUser;
  } catch {
    return null;
  }
}

export function saveLocalUser(user: LocalUser): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

export function clearLocalUser(): void {
  localStorage.removeItem(STORAGE_KEY);
}

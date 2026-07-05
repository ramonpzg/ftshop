import { createContext, useContext } from "react";
import type { LocalUser } from "../data/localUser";

export const CurrentUserContext = createContext<LocalUser | null>(null);

export function useCurrentUser(): LocalUser | null {
  return useContext(CurrentUserContext);
}

import { createContext, useContext } from "react";

export interface PresenterContextValue {
  locked: boolean;
  /** Bumped whenever a page is reset, so mounted workspace panels refetch. */
  resetToken: number;
}

export const PresenterContext = createContext<PresenterContextValue>({
  locked: false,
  resetToken: 0,
});

export function usePresenterState(): PresenterContextValue {
  return useContext(PresenterContext);
}

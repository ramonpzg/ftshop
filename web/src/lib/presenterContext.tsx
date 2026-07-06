import { createContext, useContext } from "react";

export interface PresenterContextValue {
  locked: boolean;
  /** Bumped whenever a page is reset, so mounted workspace panels refetch. */
  resetToken: number;
  /** True for the client opened with ?presenter=1. A convenience, not auth. */
  isPresenter: boolean;
}

export const PresenterContext = createContext<PresenterContextValue>({
  locked: false,
  resetToken: 0,
  isPresenter: false,
});

export function usePresenterState(): PresenterContextValue {
  return useContext(PresenterContext);
}

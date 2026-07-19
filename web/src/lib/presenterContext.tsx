import { createContext, useContext } from "react";

export interface PresenterContextValue {
  locked: boolean;
  /** Bumped whenever a page is reset, so mounted workspace panels refetch. */
  resetToken: number;
  /** True for the client opened with ?presenter=1. A convenience, not auth. */
  isPresenter: boolean;
  /** The room's shared mode from presenter state: idle, presenter, or
   * workspaces. Slide controls broadcast targets only while "presenter". */
  presenterMode: string;
}

export const PresenterContext = createContext<PresenterContextValue>({
  locked: false,
  resetToken: 0,
  isPresenter: false,
  presenterMode: "idle",
});

export function usePresenterState(): PresenterContextValue {
  return useContext(PresenterContext);
}

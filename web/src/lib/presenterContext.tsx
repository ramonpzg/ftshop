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
  /** Surfaces a concise transient message in the status area. Used for
   * failures the presenter must not stay blind to, like a slide
   * broadcast that never reached the room. */
  reportNotice: (notice: string) => void;
}

export const PresenterContext = createContext<PresenterContextValue>({
  locked: false,
  resetToken: 0,
  isPresenter: false,
  presenterMode: "idle",
  reportNotice: () => {},
});

export function usePresenterState(): PresenterContextValue {
  return useContext(PresenterContext);
}

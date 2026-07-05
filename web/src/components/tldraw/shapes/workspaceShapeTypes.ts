import { T, type TLBaseShape } from "tldraw";

export type WorkspaceShape = TLBaseShape<
  "workspace",
  {
    w: number;
    h: number;
    workspaceId: string;
    userId: string;
    userName: string;
    pageSlug: string;
  }
>;

export const workspaceShapeProps = {
  w: T.number,
  h: T.number,
  workspaceId: T.string,
  userId: T.string,
  userName: T.string,
  pageSlug: T.string,
};

/** The store schema for the workshop room, built without an Editor so
 * the sync server (and tests) can validate and migrate records. The
 * custom shape props come from the same modules the client's shape
 * utils use, so the two sides cannot drift. */

import { createTLSchema, defaultShapeSchemas } from "@tldraw/tlschema";
import { deckShapeProps } from "../src/components/tldraw/shapes/deckShapeTypes";
import { modalityPanelShapeProps } from "../src/components/tldraw/shapes/modalityPanelShapeTypes";
import { notebookShapeProps } from "../src/components/tldraw/shapes/notebookShapeTypes";
import { workspaceShapeProps } from "../src/components/tldraw/shapes/workspaceShapeTypes";

export function createRoomSchema() {
  return createTLSchema({
    shapes: {
      ...defaultShapeSchemas,
      workspace: { props: workspaceShapeProps },
      "modality-panel": { props: modalityPanelShapeProps },
      "notebook-panel": { props: notebookShapeProps },
      "deck-panel": { props: deckShapeProps },
    },
  });
}

/** The tldraw schema sequence versions this runtime understands, used by
 * the migration pre-step to detect snapshots from a newer tldraw. */
export function runtimeSchemaSequences(): Record<string, number> {
  return createRoomSchema().serialize().sequences;
}

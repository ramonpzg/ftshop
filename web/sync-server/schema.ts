/** The store schema for the workshop room, built without an Editor so
 * the sync server (and tests) can validate and migrate records. The
 * custom shape props come from the same modules the client's shape
 * utils use, so the two sides cannot drift. */

import type { SerializedSchema, SerializedStore } from "@tldraw/store";
import type { TLRecord } from "@tldraw/tlschema";
import { createTLSchema, defaultShapeSchemas } from "@tldraw/tlschema";
import {
  type CanvasDocumentSnapshot,
  CanvasMigrationError,
} from "../src/calculations/canvasMigrations";
import { adaptationPanelShapeProps } from "../src/components/tldraw/shapes/adaptationPanelShapeTypes";
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
      "adaptation-panel": { props: adaptationPanelShapeProps },
    },
  });
}

/** The tldraw schema sequence versions this runtime understands, used by
 * the migration pre-step to detect snapshots from a newer tldraw. */
export function runtimeSchemaSequences(): Record<string, number> {
  return createRoomSchema().serialize().sequences;
}

export interface ValidatedRoomDocument {
  store: SerializedStore<TLRecord>;
  schema: SerializedSchema;
  /** True when tldraw's own migrator changed anything (older sequences
   * brought up to date), meaning the disk copy is out of date. */
  upgraded: boolean;
}

function sameSequences(a: Record<string, number>, b: Record<string, number>): boolean {
  const aKeys = Object.keys(a);
  return aKeys.length === Object.keys(b).length && aKeys.every((key) => a[key] === b[key]);
}

/**
 * The last gate before a document reaches the room: run tldraw's own
 * snapshot migrator, then validate every record against the real
 * validators. Type-name checks in the migration pipeline cannot see a
 * malformed record of a known type (a note with empty props, say);
 * this can, and a document that fails here must never open a room,
 * because every connecting client would choke on it. Throws
 * CanvasMigrationError; the caller leaves the stored snapshot alone.
 */
export function upgradeAndValidateDocument(
  snapshot: CanvasDocumentSnapshot,
  schema = createRoomSchema(),
): ValidatedRoomDocument {
  const result = schema.migrateStoreSnapshot({
    store: snapshot.store as unknown as SerializedStore<TLRecord>,
    schema: snapshot.schema as unknown as SerializedSchema,
  });
  if (result.type !== "success") {
    throw new CanvasMigrationError(
      `tldraw could not migrate the stored canvas (${result.reason}); refusing to load`,
    );
  }

  const types = schema.types as Record<string, { validate(record: unknown): unknown } | undefined>;
  for (const record of Object.values(result.value)) {
    const recordType = types[record.typeName];
    if (!recordType) {
      throw new CanvasMigrationError(
        `record ${record.id} has type ${record.typeName} with no validator; refusing to load`,
      );
    }
    try {
      recordType.validate(record);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new CanvasMigrationError(
        `record ${record.id} failed validation after migration: ${message}; refusing to load`,
      );
    }
  }

  const serialized = schema.serialize();
  return {
    store: result.value,
    schema: serialized,
    upgraded: !sameSequences(snapshot.schema.sequences, serialized.sequences),
  };
}

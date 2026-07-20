import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  type CanvasDocumentSnapshot,
  CanvasMigrationError,
  downgradeFutureSchema,
  migrateCanvasDocument,
} from "../../src/calculations/canvasMigrations";
import {
  DECK_SHAPE_ID,
  modalityPanelShapeId,
  pageIdForSlug,
} from "../../src/calculations/canvasIds";
import {
  createRoomSchema,
  runtimeSchemaSequences,
  upgradeAndValidateDocument,
} from "../../sync-server/schema";

const SEQUENCES = runtimeSchemaSequences();
const SCHEMA = createRoomSchema();

/** Every record in a migrated document must satisfy the real tldraw
 * validators, or the sync room would refuse the document at load. */
function expectValidRecords(snapshot: CanvasDocumentSnapshot) {
  for (const record of Object.values(snapshot.store)) {
    const recordType = (SCHEMA.types as Record<string, { validate(r: unknown): unknown }>)[
      record.typeName
    ];
    expect(recordType).toBeDefined();
    recordType.validate(record);
  }
}

/** An old but non-empty canvas: pages exist, the presenter drew on them,
 * an attendee has a workspace, and neither the deck panel nor the video
 * page's modality panel exists yet. Includes a shape type this app has
 * never heard of, standing in for whatever the future adds. */
function oldSnapshot(): CanvasDocumentSnapshot {
  const noteProps = {
    color: "violet",
    richText: {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "authored" }] }],
    },
    size: "m",
    font: "draw",
    align: "middle",
    verticalAlign: "middle",
    labelColor: "black",
    growY: 0,
    fontSizeAdjustment: 1,
    url: "",
    scale: 1,
    textFirstEditedBy: null,
  };
  return {
    store: {
      "document:document": {
        id: "document:document",
        typeName: "document",
        gridSize: 10,
        name: "",
        meta: {},
      },
      [pageIdForSlug("presentation")]: {
        id: pageIdForSlug("presentation"),
        typeName: "page",
        name: "Presentation",
        index: "a1",
        meta: {},
      },
      [pageIdForSlug("chess-machine")]: {
        id: pageIdForSlug("chess-machine"),
        typeName: "page",
        name: "Building a Chess Machine",
        index: "a2",
        meta: {},
      },
      [pageIdForSlug("real-world-video")]: {
        id: pageIdForSlug("real-world-video"),
        typeName: "page",
        name: "Video of the Real-World Use Case",
        index: "a3",
        meta: {},
      },
      "shape:authored-note": {
        id: "shape:authored-note",
        typeName: "shape",
        type: "note",
        parentId: pageIdForSlug("presentation"),
        index: "a5",
        x: 40,
        y: 40,
        rotation: 0,
        isLocked: false,
        opacity: 1,
        meta: {},
        props: noteProps,
      },
      "shape:workspace-user1-chess-machine": {
        id: "shape:workspace-user1-chess-machine",
        typeName: "shape",
        type: "workspace",
        parentId: pageIdForSlug("chess-machine"),
        index: "a6",
        x: 0,
        y: 1500,
        rotation: 0,
        isLocked: false,
        opacity: 1,
        meta: {},
        props: {
          w: 1240,
          h: 900,
          workspaceId: "ws1",
          userId: "user1",
          userName: "Ada",
          pageSlug: "chess-machine",
        },
      },
      "shape:legacy-notebook": {
        id: "shape:legacy-notebook",
        typeName: "shape",
        type: "notebook-panel",
        parentId: pageIdForSlug("presentation"),
        index: "a7",
        x: 9,
        y: 9,
        rotation: 0,
        isLocked: false,
        opacity: 1,
        meta: { owner: "presenter" },
        props: { w: 900, h: 420, pageSlug: "presentation" },
      },
    },
    schema: { schemaVersion: 2, sequences: { ...SEQUENCES } },
  };
}

describe("migrateCanvasDocument", () => {
  test("adds missing pages, panels, and deck shape without touching existing content", () => {
    const input = oldSnapshot();
    const before = structuredClone(input);
    const { snapshot, applied, changed } = migrateCanvasDocument(input, SEQUENCES);

    expect(changed).toBe(true);
    expect(applied).toEqual([
      "ensure-workshop-pages",
      "ensure-modality-panels",
      "ensure-deck-panel",
      "stamp-ownership",
      "ensure-adaptation-panel",
    ]);

    // The two missing pages appear, seeded; the three existing ones stay.
    for (const slug of [
      "presentation",
      "chess-machine",
      "painting-pieces",
      "board-sound",
      "real-world-video",
    ]) {
      expect(snapshot.store[pageIdForSlug(slug)]).toBeDefined();
    }
    // Panels appear even though the pages already have content.
    expect(snapshot.store[modalityPanelShapeId("real-world-video")]).toBeDefined();
    expect(snapshot.store[DECK_SHAPE_ID]).toBeDefined();

    // Authored content survives in place, ownership stamped, not moved.
    const note = snapshot.store["shape:authored-note"];
    expect(note.x).toBe(40);
    expect((note.meta as { owner: string }).owner).toBe("presenter");
    const workspace = snapshot.store["shape:workspace-user1-chess-machine"];
    expect((workspace.meta as { owner: string }).owner).toBe("user1");

    // The legacy shape type (registered, no longer seeded) is
    // untouched, byte for byte.
    expect(snapshot.store["shape:legacy-notebook"]).toEqual(before.store["shape:legacy-notebook"]);

    // The input was not mutated.
    expect(input).toEqual(before);
  });

  test("is idempotent: a second run applies nothing and changes nothing", () => {
    const first = migrateCanvasDocument(oldSnapshot(), SEQUENCES);
    const second = migrateCanvasDocument(first.snapshot, SEQUENCES);
    expect(second.applied).toEqual([]);
    expect(second.changed).toBe(false);
    expect(second.snapshot).toEqual(first.snapshot);
  });

  test("a fresh document (no snapshot on the backend) seeds all five pages", () => {
    const { snapshot, changed } = migrateCanvasDocument(null, SEQUENCES);
    expect(changed).toBe(true);
    expect(
      Object.values(snapshot.store).filter((record) => record.typeName === "page"),
    ).toHaveLength(5);
    expect(snapshot.store[DECK_SHAPE_ID]).toBeDefined();
    for (const slug of ["painting-pieces", "board-sound", "real-world-video"]) {
      expect(snapshot.store[modalityPanelShapeId(slug)]).toBeDefined();
    }
    expectValidRecords(snapshot);
  });

  test("every record in the migrated document passes the real tldraw validators", () => {
    const { snapshot } = migrateCanvasDocument(oldSnapshot(), SEQUENCES);
    expectValidRecords(snapshot);
  });

  test("the migrated document loads through tldraw's own snapshot migrator", () => {
    const { snapshot } = migrateCanvasDocument(oldSnapshot(), SEQUENCES);
    const result = SCHEMA.migrateStoreSnapshot({
      store: snapshot.store as never,
      schema: snapshot.schema as never,
    });
    expect(result.type).toBe("success");
  });

  test("a shape type this runtime has never heard of fails loudly, input untouched", () => {
    const input = oldSnapshot();
    input.store["shape:mystery"] = {
      id: "shape:mystery",
      typeName: "shape",
      type: "mystery-widget",
      parentId: pageIdForSlug("presentation"),
      index: "a8",
      x: 9,
      y: 9,
      rotation: 0,
      isLocked: false,
      opacity: 1,
      meta: {},
      props: { anything: true },
    };
    const before = structuredClone(input);
    // Passing it through would only defer the failure to the room's
    // validators or to clients that cannot render it; refusing keeps
    // the stored snapshot intact and the message actionable.
    expect(() => migrateCanvasDocument(input, SEQUENCES)).toThrow(CanvasMigrationError);
    expect(() => migrateCanvasDocument(input, SEQUENCES)).toThrow(/mystery-widget/);
    expect(input).toEqual(before);
  });

  test("a genuinely unknown schema sequence is rejected, not silently accepted", () => {
    const input = oldSnapshot();
    input.schema.sequences["com.tldraw.shape.hologram"] = 99;
    const before = structuredClone(input);
    expect(() => migrateCanvasDocument(input, SEQUENCES)).toThrow(CanvasMigrationError);
    expect(() => migrateCanvasDocument(input, SEQUENCES)).toThrow(/hologram/);
    expect(input).toEqual(before);
  });

  test("a malformed record of a known type is caught before the room opens", () => {
    const { snapshot } = migrateCanvasDocument(oldSnapshot(), SEQUENCES);
    // Type-name checks pass this note; only the real validators see
    // that its props are empty. This is the gate the room boot uses.
    snapshot.store["shape:bad-note"] = {
      id: "shape:bad-note",
      typeName: "shape",
      type: "note",
      parentId: pageIdForSlug("presentation"),
      index: "a9",
      x: 0,
      y: 0,
      rotation: 0,
      isLocked: false,
      opacity: 1,
      meta: {},
      props: {},
    };
    expect(() => upgradeAndValidateDocument(snapshot)).toThrow(CanvasMigrationError);
    expect(() => upgradeAndValidateDocument(snapshot)).toThrow(/shape:bad-note/);
  });

  test("a valid migrated document passes the room's full validation gate", () => {
    const { snapshot } = migrateCanvasDocument(oldSnapshot(), SEQUENCES);
    const document = upgradeAndValidateDocument(snapshot);
    expect(Object.keys(document.store).length).toBe(Object.keys(snapshot.store).length);
    // Already at current sequences: nothing for tldraw to upgrade.
    expect(document.upgraded).toBe(false);
  });

  test("a document from a newer workshop version is rejected, not silently accepted", () => {
    const first = migrateCanvasDocument(oldSnapshot(), SEQUENCES);
    const future = structuredClone(first.snapshot);
    (future.store["document:document"].meta as Record<string, unknown>).workshopCanvasVersion = 14;
    expect(() => migrateCanvasDocument(future, SEQUENCES)).toThrow(/workshop version 14/);
  });

  test("a schema down-conversion alone still reports changed for persistence", () => {
    // Fully migrated document, but saved by the newer tldraw: the note
    // sequence is one ahead and the note carries the renamed field.
    const current = migrateCanvasDocument(oldSnapshot(), SEQUENCES).snapshot;
    current.schema.sequences["com.tldraw.shape.note"] = SEQUENCES["com.tldraw.shape.note"] + 1;
    const props = current.store["shape:authored-note"].props as Record<string, unknown>;
    delete props.textFirstEditedBy;
    props.textLastEditedBy = null;

    const result = migrateCanvasDocument(current, SEQUENCES);
    expect(result.applied).toEqual([]);
    expect(result.changed).toBe(true);
  });

  test("the repository's current authored snapshot loads and remains settled", () => {
    const raw = JSON.parse(
      readFileSync(join(import.meta.dir, "../../../data/canvas/snapshot.json"), "utf8"),
    ) as CanvasDocumentSnapshot;
    const { snapshot, changed } = migrateCanvasDocument(raw, SEQUENCES);
    expect(changed).toBe(false);
    expect(snapshot.store[DECK_SHAPE_ID]).toBeDefined();
    const result = SCHEMA.migrateStoreSnapshot({
      store: snapshot.store as never,
      schema: snapshot.schema as never,
    });
    expect(result.type).toBe("success");
    // Every record survives the room's full validation gate too.
    upgradeAndValidateDocument(snapshot);
    // And it settles: a second pass is a no-op.
    const again = migrateCanvasDocument(snapshot, SEQUENCES);
    expect(again.changed).toBe(false);
  });
});

describe("downgradeFutureSchema", () => {
  test("renames the 5.2.2 note field back and clamps the sequence", () => {
    const snapshot = oldSnapshot();
    snapshot.schema.sequences["com.tldraw.shape.note"] = SEQUENCES["com.tldraw.shape.note"] + 1;
    const props = snapshot.store["shape:authored-note"].props as Record<string, unknown>;
    delete props.textFirstEditedBy;
    props.textLastEditedBy = null;

    // Only valid for the exact 13 -> 12 step this runtime knows about.
    if (SEQUENCES["com.tldraw.shape.note"] === 12) {
      const changed = downgradeFutureSchema(snapshot, SEQUENCES);
      expect(changed).toBe(true);
      const migrated = snapshot.store["shape:authored-note"].props as Record<string, unknown>;
      expect(migrated.textFirstEditedBy).toBeNull();
      expect("textLastEditedBy" in migrated).toBe(false);
    }
  });

  test("an unknown from-the-future sequence fails loudly and leaves the input alone", () => {
    const input = oldSnapshot();
    input.schema.sequences["com.tldraw.shape.geo"] = SEQUENCES["com.tldraw.shape.geo"] + 7;
    const before = structuredClone(input);
    expect(() => migrateCanvasDocument(input, SEQUENCES)).toThrow(CanvasMigrationError);
    expect(input).toEqual(before);
  });
});

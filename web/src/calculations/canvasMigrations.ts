/** Versioned, idempotent migrations for the shared canvas document.
 *
 * "Seed only when empty" could never add a shape to a page that already
 * had content, which is how existing canvases missed the deck panel and
 * modality panels. This module replaces it: the document carries an
 * explicit workshop version in the document record's meta, and ordered
 * migrations bring any snapshot up to date without moving or deleting
 * what a presenter or attendee already made.
 *
 * The sync server runs this once at room load, before any client
 * connects. A thrown CanvasMigrationError aborts the load; the caller
 * must leave the stored snapshot untouched in that case.
 */

import { PAGES } from "../lib/pages";
import {
  DECK_SHAPE_ID,
  DOCUMENT_RECORD_ID,
  modalityPanelShapeId,
  pageIdForSlug,
  seedIndex,
  seedPromptShapeId,
  seedShapeId,
} from "./canvasIds";
import { PRESENTER_OWNER } from "./canvasOwnership";
import {
  buildDeckPanelRecord,
  buildDocumentRecord,
  buildFrameRecord,
  buildModalityPanelRecord,
  buildNoteRecord,
  buildPageRecord,
  buildTextRecord,
  type CanvasRecord,
} from "./canvasRecords";
import { getPageSeedShapes, type SeedShape } from "./pageSeeds";

export class CanvasMigrationError extends Error {}

export interface CanvasDocumentSnapshot {
  store: Record<string, CanvasRecord>;
  schema: {
    schemaVersion: number;
    sequences: Record<string, number>;
  };
}

export const CANVAS_DOCUMENT_VERSION = 4;

const VERSION_META_KEY = "workshopCanvasVersion";

type StoreRecords = Record<string, CanvasRecord>;

interface CanvasMigration {
  version: number;
  name: string;
  migrate(store: StoreRecords): void;
}

function shapeMeta(record: CanvasRecord): Record<string, unknown> {
  const meta = record.meta;
  return typeof meta === "object" && meta !== null ? (meta as Record<string, unknown>) : {};
}

function shapesOfType(store: StoreRecords, type: string): CanvasRecord[] {
  return Object.values(store).filter((r) => r.typeName === "shape" && r.type === type);
}

/**
 * Compatibility pre-step, separate from the versioned list because it
 * depends on the snapshot's tldraw schema rather than the workshop
 * version. The initial authored snapshot was saved by tldraw 5.2.2; this
 * runtime is pinned at 5.1.1, whose loader refuses sequences from
 * the future. Exactly three sequences moved between those versions, and
 * each is losslessly reversible for the content this app produces:
 *
 * - note 13 renamed textFirstEditedBy to textLastEditedBy; renaming it
 *   back is the upstream down migration verbatim.
 * - draw 5 and highlight 4 added an optional `dim` field to segments.
 *   Segments without `dim` are already valid 5.1.1 records; segments
 *   with it would need tldraw's base64 path codec, so those fail loudly
 *   instead of being guessed at.
 *
 * Any other from-the-future sequence throws: refusing to load beats
 * silently corrupting an authored document.
 */
export function downgradeFutureSchema(
  snapshot: CanvasDocumentSnapshot,
  runtimeSequences: Record<string, number>,
): boolean {
  let changed = false;
  for (const [sequence, snapshotVersion] of Object.entries(snapshot.schema.sequences)) {
    const runtimeVersion = runtimeSequences[sequence];
    if (runtimeVersion === undefined) {
      // A sequence this runtime has never heard of means the document
      // was authored by a newer or foreign build. Its records may be
      // absent today, but accepting the schema would still claim we
      // can represent a document we cannot.
      throw new CanvasMigrationError(
        `snapshot uses schema sequence ${sequence} (version ${snapshotVersion}) ` +
          "that this runtime does not know; refusing to load",
      );
    }
    if (snapshotVersion <= runtimeVersion) continue;

    if (sequence === "com.tldraw.shape.note" && snapshotVersion === 13 && runtimeVersion === 12) {
      for (const note of shapesOfType(snapshot.store, "note")) {
        const props = note.props as Record<string, unknown>;
        if ("textLastEditedBy" in props) {
          props.textFirstEditedBy = props.textLastEditedBy ?? null;
          delete props.textLastEditedBy;
        }
      }
      snapshot.schema.sequences[sequence] = runtimeVersion;
      changed = true;
      continue;
    }

    const strippable =
      (sequence === "com.tldraw.shape.draw" && snapshotVersion === 5 && runtimeVersion === 4) ||
      (sequence === "com.tldraw.shape.highlight" && snapshotVersion === 4 && runtimeVersion === 3);
    if (strippable) {
      const type = sequence.split(".").at(-1) as string;
      for (const shape of shapesOfType(snapshot.store, type)) {
        const segments = (shape.props as { segments?: Array<Record<string, unknown>> }).segments;
        if (segments?.some((segment) => "dim" in segment)) {
          throw new CanvasMigrationError(
            `cannot downgrade ${sequence}: a ${type} shape uses the newer segment encoding`,
          );
        }
      }
      snapshot.schema.sequences[sequence] = runtimeVersion;
      changed = true;
      continue;
    }

    throw new CanvasMigrationError(
      `snapshot schema sequence ${sequence} is version ${snapshotVersion}, ` +
        `newer than this runtime's ${runtimeVersion}, with no known down conversion`,
    );
  }
  return changed;
}

/**
 * Refuses records this runtime cannot represent: a record, shape,
 * binding, or asset type absent from the runtime schema would pass
 * through migration only to be rejected by the room's validators or,
 * worse, shipped to clients that cannot render it. Failing here keeps
 * the stored snapshot untouched and the error message actionable. The
 * realistic source of such a record is running an older build against
 * a canvas authored by a newer one.
 */
export function assertKnownRecordTypes(
  store: StoreRecords,
  runtimeSequences: Record<string, number>,
): void {
  for (const record of Object.values(store)) {
    if (!(`com.tldraw.${record.typeName}` in runtimeSequences)) {
      throw new CanvasMigrationError(
        `unknown record type ${record.typeName} (${record.id}); refusing to load`,
      );
    }
    const isSubtyped = ["shape", "asset", "binding"].includes(record.typeName);
    const subtype = record.type;
    if (
      isSubtyped &&
      !(
        typeof subtype === "string" &&
        `com.tldraw.${record.typeName}.${subtype}` in runtimeSequences
      )
    ) {
      throw new CanvasMigrationError(
        `unknown ${record.typeName} type ${String(subtype)} (${record.id}); ` +
          "this canvas needs a newer build, refusing to load",
      );
    }
  }
}

function seedShapeRecords(slug: string): CanvasRecord[] {
  const pageId = pageIdForSlug(slug);
  const records: CanvasRecord[] = [];
  const seeds = getPageSeedShapes(slug);
  seeds.forEach((seed: SeedShape, index: number) => {
    const base = {
      id: seedShapeId(slug, index),
      parentId: pageId,
      index: seedIndex(index + 1),
      x: seed.x,
      y: seed.y,
    };
    if (seed.kind === "heading") {
      records.push(buildTextRecord(base, seed.text, { size: index === 0 ? "xl" : "m", w: 820 }));
    } else if (seed.kind === "frame") {
      records.push(buildFrameRecord(base, { w: seed.w, h: seed.h, name: seed.name }));
      records.push(
        buildTextRecord(
          {
            id: seedPromptShapeId(slug, index),
            parentId: base.id,
            index: seedIndex(1),
            x: 80,
            y: 80,
          },
          seed.prompt,
          { size: "m", w: seed.w - 160 },
        ),
      );
    } else {
      records.push(buildNoteRecord(base, seed.text, seed.color ?? "yellow"));
    }
  });
  return records;
}

const MODALITY_PANEL_MODALITIES = new Set(["image", "audio", "video"]);

const CANVAS_MIGRATIONS: CanvasMigration[] = [
  {
    version: 1,
    name: "ensure-workshop-pages",
    migrate(store) {
      PAGES.forEach((page, order) => {
        const pageId = pageIdForSlug(page.slug);
        if (store[pageId]) return;
        store[pageId] = buildPageRecord(page.slug, page.title, seedIndex(order + 1));
        for (const record of seedShapeRecords(page.slug)) {
          store[record.id] = record;
        }
      });
    },
  },
  {
    version: 2,
    name: "ensure-modality-panels",
    migrate(store) {
      for (const page of PAGES) {
        if (!MODALITY_PANEL_MODALITIES.has(page.modality)) continue;
        const id = modalityPanelShapeId(page.slug);
        if (store[id]) continue;
        store[id] = buildModalityPanelRecord(
          // Below the seeded note rows, clear of the workspace grid.
          { id, parentId: pageIdForSlug(page.slug), index: seedIndex(90), x: 0, y: 1200 },
          { modality: page.modality, pageSlug: page.slug },
        );
      }
    },
  },
  {
    version: 3,
    name: "ensure-deck-panel",
    migrate(store) {
      if (store[DECK_SHAPE_ID]) return;
      const presentationPageId = pageIdForSlug(PAGES[0].slug);
      if (!store[presentationPageId]) return;
      store[DECK_SHAPE_ID] = buildDeckPanelRecord(
        // Below the seeded slide-sketch row (y=1400, 900 tall).
        {
          id: DECK_SHAPE_ID,
          parentId: presentationPageId,
          index: seedIndex(91),
          x: 0,
          y: 2450,
        },
        "http://localhost:3030",
      );
    },
  },
  {
    version: 4,
    name: "stamp-ownership",
    migrate(store) {
      for (const record of Object.values(store)) {
        if (record.typeName === "page") {
          const meta = shapeMeta(record);
          if (typeof meta.owner !== "string") record.meta = { ...meta, owner: PRESENTER_OWNER };
          continue;
        }
        if (record.typeName !== "shape") continue;
        const meta = shapeMeta(record);
        if (typeof meta.owner === "string") continue;
        const owner =
          record.type === "workspace"
            ? ((record.props as { userId?: string }).userId ?? PRESENTER_OWNER)
            : PRESENTER_OWNER;
        record.meta = { ...meta, owner };
      }
    },
  },
];

export interface CanvasMigrationResult {
  snapshot: CanvasDocumentSnapshot;
  /** Names of the migration steps that ran, in order. Empty when the
   * document was already current. */
  applied: string[];
  changed: boolean;
}

function readVersion(store: StoreRecords): number {
  const document = store[DOCUMENT_RECORD_ID];
  if (!document) return 0;
  const version = shapeMeta(document)[VERSION_META_KEY];
  return typeof version === "number" && Number.isInteger(version) ? version : 0;
}

function writeVersion(store: StoreRecords, version: number): void {
  const document = store[DOCUMENT_RECORD_ID] ?? buildDocumentRecord();
  document.meta = { ...shapeMeta(document), [VERSION_META_KEY]: version };
  store[DOCUMENT_RECORD_ID] = document;
}

/**
 * Migrates a stored canvas document to the current workshop version, or
 * builds a fresh one when the backend has no snapshot yet. The input is
 * never mutated; on any thrown error the caller still holds the original.
 */
export function migrateCanvasDocument(
  input: CanvasDocumentSnapshot | null,
  runtimeSequences: Record<string, number>,
): CanvasMigrationResult {
  const snapshot: CanvasDocumentSnapshot = input
    ? structuredClone(input)
    : {
        store: { [DOCUMENT_RECORD_ID]: buildDocumentRecord() },
        schema: { schemaVersion: 2, sequences: { ...runtimeSequences } },
      };

  const downgraded = input ? downgradeFutureSchema(snapshot, runtimeSequences) : false;
  assertKnownRecordTypes(snapshot.store, runtimeSequences);

  const startVersion = readVersion(snapshot.store);
  if (startVersion > CANVAS_DOCUMENT_VERSION) {
    // A document from a newer build. Silently "succeeding" here would
    // open the room on content this runtime does not understand.
    throw new CanvasMigrationError(
      `canvas is at workshop version ${startVersion}, newer than this ` +
        `runtime's ${CANVAS_DOCUMENT_VERSION}; refusing to load`,
    );
  }
  const applied: string[] = [];
  for (const migration of CANVAS_MIGRATIONS) {
    if (migration.version <= startVersion) continue;
    migration.migrate(snapshot.store);
    applied.push(migration.name);
  }
  if (applied.length > 0) writeVersion(snapshot.store, CANVAS_DOCUMENT_VERSION);

  return { snapshot, applied, changed: downgraded || applied.length > 0 };
}

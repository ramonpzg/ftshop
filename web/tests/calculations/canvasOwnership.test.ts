import { describe, expect, test } from "bun:test";
import {
  type CanvasActor,
  canChangeRecord,
  canCreateRecord,
  canDeleteRecord,
  ownerForNewShape,
  recordOwner,
} from "../../src/calculations/canvasOwnership";

const presenter: CanvasActor = { isPresenter: true, userId: "u-presenter" };
const ada: CanvasActor = { isPresenter: false, userId: "user-ada" };
const grace: CanvasActor = { isPresenter: false, userId: "user-grace" };
const watcher: CanvasActor = { isPresenter: false, userId: null };

function shape(owner?: string, extra: Record<string, unknown> = {}) {
  return {
    id: "shape:x",
    typeName: "shape",
    meta: owner === undefined ? {} : { owner },
    ...extra,
  };
}

describe("canvas ownership", () => {
  test("records without an owner belong to the presenter", () => {
    expect(recordOwner(shape())).toBe("presenter");
    expect(recordOwner(shape("user-ada"))).toBe("user-ada");
  });

  test("attendees own what they create; watchers and presenters stamp presenter", () => {
    expect(ownerForNewShape(ada)).toBe("user-ada");
    expect(ownerForNewShape(presenter)).toBe("presenter");
    expect(ownerForNewShape(watcher)).toBe("presenter");
  });

  test("an attendee edits and deletes only their own shapes", () => {
    const own = shape("user-ada");
    const theirs = shape("user-grace");
    const authored = shape("presenter");
    expect(canChangeRecord(ada, own, own)).toBe(true);
    expect(canDeleteRecord(ada, own)).toBe(true);
    expect(canChangeRecord(ada, theirs, theirs)).toBe(false);
    expect(canDeleteRecord(ada, theirs)).toBe(false);
    expect(canChangeRecord(ada, authored, authored)).toBe(false);
    expect(canDeleteRecord(ada, authored)).toBe(false);
    expect(canCreateRecord(grace, shape("user-grace"))).toBe(true);
    expect(canCreateRecord(grace, shape("user-ada"))).toBe(false);
  });

  test("attendees cannot touch pages or the document record", () => {
    const page = { id: "page:p", typeName: "page", meta: {} };
    const doc = { id: "document:document", typeName: "document", meta: {} };
    for (const record of [page, doc]) {
      expect(canCreateRecord(ada, record)).toBe(false);
      expect(canChangeRecord(ada, record, record)).toBe(false);
      expect(canDeleteRecord(ada, record)).toBe(false);
      expect(canChangeRecord(presenter, record, record)).toBe(true);
    }
  });

  test("ownership cannot be reassigned and locks cannot be flipped by attendees", () => {
    const before = shape("user-ada", { isLocked: false });
    expect(canChangeRecord(ada, before, shape("user-grace", { isLocked: false }))).toBe(false);
    expect(canChangeRecord(ada, before, shape("user-ada", { isLocked: true }))).toBe(false);
    expect(canChangeRecord(presenter, before, shape("user-grace", { isLocked: true }))).toBe(true);
  });

  test("a watcher who never joined cannot write at all", () => {
    expect(canCreateRecord(watcher, shape("presenter"))).toBe(false);
    expect(canChangeRecord(watcher, shape(), shape())).toBe(false);
    expect(canDeleteRecord(watcher, shape())).toBe(false);
  });

  test("assets upload for everyone, update for everyone, delete only for the presenter", () => {
    const asset = { id: "asset:a", typeName: "asset", meta: {} };
    expect(canCreateRecord(ada, asset)).toBe(true);
    expect(canChangeRecord(ada, asset, asset)).toBe(true);
    expect(canDeleteRecord(ada, asset)).toBe(false);
    expect(canDeleteRecord(presenter, asset)).toBe(true);
  });

  test("the presenter can do everything", () => {
    expect(canChangeRecord(presenter, shape("user-ada"), shape("user-ada"))).toBe(true);
    expect(canDeleteRecord(presenter, shape("user-grace"))).toBe(true);
    expect(canCreateRecord(presenter, shape("presenter"))).toBe(true);
  });
});

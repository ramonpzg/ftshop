import { describe, expect, test } from "bun:test";
import { assetFileName } from "../../src/calculations/assetNames";

const SAFE_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

describe("assetFileName", () => {
  test("uses the asset id and the original extension", () => {
    expect(assetFileName("asset:abc123", "board photo.PNG", "image/png")).toBe(
      "asset-abc123.png",
    );
  });

  test("falls back to the mime type when the file name has no usable extension", () => {
    expect(assetFileName("asset:abc123", "pasted", "image/webp")).toBe("asset-abc123.webp");
    expect(assetFileName("asset:abc123", "", "video/mp4")).toBe("asset-abc123.mp4");
  });

  test("drops unsafe characters from the id", () => {
    const name = assetFileName("asset:_a/b:c!", "x.png", "image/png");
    expect(name).toBe("asset-_abc.png");
    expect(name).toMatch(SAFE_NAME);
  });

  test("unknown mime and no extension still yields a safe name", () => {
    const name = assetFileName("asset:zz9", "blob", "application/x-thing");
    expect(name).toBe("asset-zz9");
    expect(name).toMatch(SAFE_NAME);
  });

  test("hidden-file style names do not produce a leading dot extension", () => {
    const name = assetFileName("asset:a1", ".env", "image/png");
    expect(name).toBe("asset-a1.png");
    expect(name).toMatch(SAFE_NAME);
  });
});

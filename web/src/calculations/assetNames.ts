/** Pure naming for uploaded canvas assets. Must satisfy the backend's safe-name rule:
 * start alphanumeric, then only [A-Za-z0-9._-]. */

const MIME_EXTENSIONS: Record<string, string> = {
  "image/png": ".png",
  "image/jpeg": ".jpg",
  "image/gif": ".gif",
  "image/webp": ".webp",
  "image/svg+xml": ".svg",
  "video/mp4": ".mp4",
  "video/webm": ".webm",
  "audio/mpeg": ".mp3",
  "audio/wav": ".wav",
  "audio/ogg": ".ogg",
};

function extensionFor(fileName: string, mimeType: string): string {
  const dot = fileName.lastIndexOf(".");
  if (dot > 0) {
    const ext = fileName.slice(dot + 1);
    if (/^[A-Za-z0-9]{1,8}$/.test(ext)) return `.${ext.toLowerCase()}`;
  }
  return MIME_EXTENSIONS[mimeType] ?? "";
}

/**
 * Stable server-side file name for a tldraw asset. Keyed by the asset id so
 * re-uploading the same asset overwrites instead of accumulating copies.
 */
export function assetFileName(assetId: string, fileName: string, mimeType: string): string {
  const idPart = assetId.replace(/^asset:/, "").replace(/[^A-Za-z0-9._-]/g, "");
  return `asset-${idPart}${extensionFor(fileName, mimeType)}`;
}

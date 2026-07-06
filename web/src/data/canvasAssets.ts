import type { TLAssetStore } from "tldraw";
import { assetFileName } from "../calculations/assetNames";
import { canvasAssetUrl, uploadCanvasAsset } from "./api";

/**
 * Stores canvas assets (dropped images, video, audio) on the backend, on
 * disk under data/assets/. The src saved into the document is a relative
 * URL, so any client that can reach the app can fetch the asset. This is
 * what makes the presenter's slide assets survive restarts, browser
 * changes, and serving over the venue network.
 */
export const backendAssetStore: TLAssetStore = {
  async upload(asset, file) {
    const name = assetFileName(asset.id, file.name, file.type);
    await uploadCanvasAsset(name, file);
    return { src: canvasAssetUrl(name) };
  },
  resolve(asset) {
    return asset.props.src;
  },
};

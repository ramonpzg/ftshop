/** Resolves the deck URL for the machine actually viewing it.
 *
 * The deck-panel shape stores one URL for the whole synced room, and the
 * presenter's convenient default is localhost:3030. An attendee opening
 * the app from the presenter's LAN address would ask their own machine
 * for the deck, which is not running one. When the app itself is not
 * being viewed on localhost, a localhost deck URL is rewritten to the
 * app's hostname; explicit non-local URLs are respected as written.
 */

const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "[::1]"]);

export function resolveDeckUrl(configuredUrl: string, currentHostname: string): string {
  let url: URL;
  try {
    url = new URL(configuredUrl);
  } catch {
    return configuredUrl;
  }
  if (!LOCAL_HOSTNAMES.has(url.hostname)) return configuredUrl;
  if (LOCAL_HOSTNAMES.has(currentHostname) || currentHostname.length === 0) return configuredUrl;
  url.hostname = currentHostname;
  return url.toString();
}

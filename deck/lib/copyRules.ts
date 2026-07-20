/** Copy checks for deck-owned text.
 *
 * This lints what a machine can honestly lint: banned punctuation and
 * a short list of genuinely unwanted stock phrases. It does not
 * pretend tone is a regex; the tone pass is editorial and happens in
 * review. Scope is deck-owned files only during the parallel stage;
 * phase 34 integration decides whether the same check widens.
 */

export interface CopyFinding {
  line: number;
  rule: string;
  excerpt: string;
}

/** Exact substrings that are always fine even though a rule below
 * would catch them. Narrow and explicit by design. */
export const ALLOWLIST: string[] = [
  // Slidev's code-morph syntax, not the AI cliche.
  "magic-move",
];

/** Stock phrases that have already appeared in this repo's copy or
 * that the phase prompt names. Case-insensitive substring match. */
export const BANNED_PHRASES: string[] = [
  "rooks before feelings",
  "gpu sulking",
  "pawns dream",
  "not vibes",
  "pocket money",
  "all yours to keep",
  "game-changing",
  "game changer",
  "democratize",
  "democratise",
  "supercharge",
  "future is here",
  "delve",
];

/** Cliche words that need a word boundary so they do not fire inside
 * ordinary words. */
export const BANNED_WORDS: string[] = ["magic", "magical", "journey", "unlock"];

const EM_DASH = /—/;

/** Emoji detection. The chess glyphs live in U+2654..U+265F, which is
 * why the Miscellaneous Symbols block (U+2600..U+26FF) is deliberately
 * not covered; the deck has no reason to carry any symbol from the
 * blocks below. */
const EMOJI = /[\u{1F000}-\u{1FAFF}\u{2700}-\u{27BF}\u{2B00}-\u{2BFF}]|️/u;

function stripAllowed(line: string): string {
  let out = line;
  for (const allowed of ALLOWLIST) {
    out = out.split(allowed).join(" ");
  }
  return out;
}

export function checkLine(line: string, lineNumber: number): CopyFinding[] {
  const findings: CopyFinding[] = [];
  const scannable = stripAllowed(line);
  const lower = scannable.toLowerCase();

  if (EM_DASH.test(scannable)) {
    findings.push({ line: lineNumber, rule: "em dash", excerpt: line.trim() });
  }
  if (EMOJI.test(scannable)) {
    findings.push({ line: lineNumber, rule: "emoji", excerpt: line.trim() });
  }
  for (const phrase of BANNED_PHRASES) {
    if (lower.includes(phrase)) {
      findings.push({ line: lineNumber, rule: `phrase: ${phrase}`, excerpt: line.trim() });
    }
  }
  for (const word of BANNED_WORDS) {
    if (new RegExp(`\\b${word}\\b`, "i").test(scannable)) {
      findings.push({ line: lineNumber, rule: `word: ${word}`, excerpt: line.trim() });
    }
  }
  return findings;
}

export function checkCopy(text: string): CopyFinding[] {
  return text.split("\n").flatMap((line, index) => checkLine(line, index + 1));
}

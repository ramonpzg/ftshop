/** Builds tldraw rich text documents from plain strings, without an
 * editor. The output matches what tldraw's toRichText produces: one
 * paragraph per line, empty lines becoming empty paragraphs. Needed by
 * the canvas migrations, which create records outside a browser. */

export interface RichTextDoc {
  type: "doc";
  content: Array<{ type: "paragraph"; content?: Array<{ type: "text"; text: string }> }>;
}

export function richTextFromLines(text: string): RichTextDoc {
  return {
    type: "doc",
    content: text.split("\n").map((line) =>
      line.length > 0
        ? { type: "paragraph" as const, content: [{ type: "text" as const, text: line }] }
        : { type: "paragraph" as const },
    ),
  };
}

// Generates public/llms-full.txt from all .astro pages in src/pages/.
// Strips HTML, keeps order from the canvas nav registry.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const PAGES = path.join(ROOT, "src/pages");
const OUTS = [
  path.join(ROOT, "llms-full.txt"),
  path.join(ROOT, "public/llms-full.txt"),
];

// Ordered list of slugs (matches nav.js registry, minus index)
const ORDER = [
  "manifesto",
  "architecture",
  "repo-structure",
  "packages",
  "api-surface",
  "database",
  "contracts",
  "payment-flow",
  "policy-engine",
  "wallet-mpc",
  "settlement",
  "checkout",
  "compliance",
  "protocols",
  "sdks",
  "integrations",
  "dashboard",
  "external",
  "cicd",
  "security",
  "protocol-objects",
  "state-machine",
  "dual-rail",
  "credit",
  "sardis-connect",
  "osp-integration",
  "zk-privacy",
];

function stripHtml(s) {
  // remove astro frontmatter
  s = s.replace(/^---[\s\S]*?---\s*/, "");
  // remove <script> and <style> blocks (repeat until stable to avoid
  // incomplete multi-character sanitization from overlapping constructions)
  let prev;
  do {
    prev = s;
    s = s.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "");
    s = s.replace(/<style[\s\S]*?<\/style>/gi, "");
  } while (s !== prev);
  // mermaid pre blocks — keep textual diagram description-ish content
  s = s.replace(/<pre[^>]*class="mermaid"[^>]*>([\s\S]*?)<\/pre>/gi, "\n[diagram]\n$1\n[/diagram]\n");
  // <br> to newline
  s = s.replace(/<br\s*\/?\s*>/gi, "\n");
  // block tags get newlines
  s = s.replace(/<\/(h1|h2|h3|h4|h5|h6|p|section|div|li|tr|td|th|dt|dd|pre|blockquote|article|header|footer|main|aside|figure|figcaption)>/gi, "\n");
  s = s.replace(/<(h1|h2|h3|h4|h5|h6)[^>]*>/gi, "\n\n## ");
  s = s.replace(/<li[^>]*>/gi, "\n- ");
  // strip remaining tags
  s = s.replace(/<[^>]+>/g, "");
  // decode common entities (decode &amp; last to avoid double-unescaping)
  s = s
    .replace(/&#123;/g, "{")
    .replace(/&#125;/g, "}")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&rsquo;/g, "'")
    .replace(/&lsquo;/g, "'")
    .replace(/&ldquo;/g, '"')
    .replace(/&rdquo;/g, '"')
    .replace(/&mdash;/g, "—")
    .replace(/&ndash;/g, "–")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&");
  // strip tags again after decoding entities to avoid reintroducing HTML-like markup
  s = s.replace(/<[^>]+>/g, "");
  // collapse whitespace
  s = s.replace(/[ \t]+/g, " ");
  s = s.replace(/\n[ \t]+/g, "\n");
  s = s.replace(/\n{3,}/g, "\n\n");
  return s.trim();
}

const header = `# Sardis Canvases — Full Text Dump

This file is the concatenated plain-text content of every canvas at canvas.sardis.sh.
Safe to paste into any large-context AI (Claude, ChatGPT, Gemini) for summarization,
Q&A, or architecture review.

Canvases are ordered as they appear in the sidebar.
Last built: ${new Date().toISOString()}

---

`;

let out = header;
for (const slug of ORDER) {
  const file = path.join(PAGES, `${slug}.astro`);
  if (!fs.existsSync(file)) continue;
  const content = fs.readFileSync(file, "utf8");
  const text = stripHtml(content);
  out += `\n\n=====================================\n# ${slug.toUpperCase().replace(/-/g, " ")}\nhttps://canvas.sardis.sh/${slug}\n=====================================\n\n${text}\n`;
}

for (const outPath of OUTS) {
  fs.writeFileSync(outPath, out);
}
const kb = (Buffer.byteLength(out) / 1024).toFixed(1);
console.log(`wrote llms-full.txt (${kb} KB, ${ORDER.length} canvases)`);

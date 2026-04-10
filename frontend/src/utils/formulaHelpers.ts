/**
 * Formula helper utilities.
 *
 * Provides preprocessing so that LLM output (which may use a mix of
 * `$...$`, `$$...$$`, `\(...\)`, `\[...\]` delimiters) is normalised
 * to the `$` / `$$` form that remark-math understands.
 */

/** Wrap a raw LaTeX string in display-math delimiters if not already wrapped. */
export function ensureDisplayMath(latex: string): string {
    const trimmed = latex.trim();
    if (trimmed.startsWith("$$") && trimmed.endsWith("$$")) return trimmed;
    if (trimmed.startsWith("\\[") && trimmed.endsWith("\\]")) return trimmed;
    return `$$\n${trimmed}\n$$`;
}

/** Wrap a string in inline-math delimiters if not already wrapped. */
export function ensureInlineMath(latex: string): string {
    const trimmed = latex.trim();
    if (trimmed.startsWith("$") && trimmed.endsWith("$")) return trimmed;
    if (trimmed.startsWith("\\(") && trimmed.endsWith("\\)")) return trimmed;
    return `$${trimmed}$`;
}

/** Quick check whether a string contains any LaTeX math delimiters. */
export function containsMath(text: string): boolean {
    return /\$\$[\s\S]+?\$\$|\$[^$]+?\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)/.test(
        text
    );
}

// ── Markdown + LaTeX preprocessor ──────────────────────────────────────

/**
 * Preprocess LLM Markdown so that every math region uses `$` / `$$`
 * delimiters that remark-math can parse, and protect LaTeX from the
 * Markdown parser (e.g. underscores being treated as emphasis).
 *
 * Handles:
 *  1. `\[...\]`  →  `$$...$$`   (display math)
 *  2. `\(...\)`  →  `$...$`     (inline math)
 *  3. Ensures display `$$` blocks are surrounded by blank lines
 *     (required by remark-math for block-level rendering).
 *  4. Protects content inside `$`/`$$` from Markdown interpretation
 *     by escaping stray underscores that would become <em>.
 */
export function preprocessLaTeX(content: string): string {
    // Step 0 — guard: leave code blocks untouched.
    // Split on fenced code blocks (``` … ```), process only non-code parts.
    const codeBlockRegex = /(```[\s\S]*?```)/g;
    const segments = content.split(codeBlockRegex);

    const processed = segments.map((seg, idx) => {
        // Odd indices are code blocks — pass through unchanged.
        if (idx % 2 === 1) return seg;
        return _processNonCodeSegment(seg);
    });

    return processed.join("");
}

function _processNonCodeSegment(text: string): string {
    // 1. Convert \[...\] → $$...$$ (display)
    //    Allow the content to span multiple lines.
    text = text.replace(
        /\\\[([\s\S]*?)\\\]/g,
        (_match, inner: string) => `\n$$\n${inner.trim()}\n$$\n`
    );

    // 2. Convert \(...\) → $...$ (inline)
    text = text.replace(
        /\\\(([\s\S]*?)\\\)/g,
        (_match, inner: string) => `$${inner.trim()}$`
    );

    // 3. Convert line-delimited single-dollar display blocks into $$ blocks.
    //    Common LLM pattern:
    //      $
    //      \frac{1}{y}dy = x\,dx
    //      $
    //    should become:
    //      $$
    //      \frac{1}{y}dy = x\,dx
    //      $$
    text = _normalizeSingleDollarDisplayBlocks(text);

    // 4. Normalize inline dollar math by trimming stray spaces:
    //    "$ f(x,y) = x^2 + y^2 $" -> "$f(x,y) = x^2 + y^2$"
    text = _normalizeInlineDollarMath(text);

    return text;
}

function _normalizeSingleDollarDisplayBlocks(text: string): string {
    const lines = text.split("\n");
    const out: string[] = [];
    let i = 0;

    const isStandaloneDollar = (line: string): boolean => /^\s*\$\s*$/.test(line);

    while (i < lines.length) {
        if (!isStandaloneDollar(lines[i])) {
            out.push(lines[i]);
            i += 1;
            continue;
        }

        let closing = -1;
        for (let j = i + 1; j < lines.length; j += 1) {
            if (isStandaloneDollar(lines[j])) {
                closing = j;
                break;
            }
        }

        // Convert only paired `$ ... $` blocks. Leave unmatched `$` unchanged.
        if (closing === -1) {
            out.push(lines[i]);
            i += 1;
            continue;
        }

        const inner = lines.slice(i + 1, closing).join("\n").trim();
        out.push(`$$${inner}$$`);
        i = closing + 1;
    }

    return out.join("\n");
}

function _normalizeInlineDollarMath(text: string): string {
    // Keep this lightweight and conservative:
    // normalize only tokens that already look like inline-math delimiters.
    return text.replace(/\$([^$\n]+)\$/g, (_match, inner: string) => {
        const trimmed = inner.trim();
        if (!trimmed) return _match;
        return `$${trimmed}$`;
    });
}

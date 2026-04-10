import React, { useEffect, useMemo, useState } from "react";
import type { VisualArtifact } from "../types/message";
import PlotRenderer from "./PlotRenderer";

const LOCAL_CHART_JS_URL = "/assets/chart.umd.js";

interface Props {
    artifact: VisualArtifact;
}

function bridgeScript(frameId: string): string {
    return `<script>
      (function () {
        const FRAME_ID = ${JSON.stringify(frameId)};
        function sendHeight() {
          try {
            const body = document.body;
            const docEl = document.documentElement;
            const h = Math.max(
              body ? body.scrollHeight : 0,
              body ? body.offsetHeight : 0,
              docEl ? docEl.scrollHeight : 0,
              docEl ? docEl.offsetHeight : 0
            );
            parent.postMessage({ type: "matopt_artifact_height", frameId: FRAME_ID, height: h }, "*");
          } catch (_) {}
        }
        window.addEventListener("load", sendHeight);
        window.addEventListener("resize", sendHeight);
        if (window.ResizeObserver) {
          const ro = new ResizeObserver(sendHeight);
          ro.observe(document.documentElement);
          if (document.body) ro.observe(document.body);
        }
        setTimeout(sendHeight, 20);
        setTimeout(sendHeight, 200);
      })();
    </script>`;
}

function wrapperStyles(): string {
    return `<style>
      :root {
        --font-sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
        --color-background-primary: #2c2c2a;
        --color-background-secondary: #1f1f1d;
        --color-border-tertiary: rgba(255,255,255,0.12);
        --color-border-secondary: rgba(255,255,255,0.2);
        --color-text-primary: #f3f3f1;
        --color-text-secondary: #bcbab2;
        --color-text-tertiary: #888780;
        --border-radius-lg: 14px;
      }
      html, body {
        margin: 0;
        padding: 0;
        background: transparent;
        color: var(--color-text-primary);
        font-family: var(--font-sans);
        line-height: 1.5;
      }
      .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        border: 0;
      }
      canvas {
        display: block;
        width: 100% !important;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin: 8px 0;
        font-size: 12px;
      }
      th, td {
        border: 0.5px solid var(--color-border-tertiary);
        padding: 8px 10px;
        text-align: left;
      }
      th {
        color: var(--color-text-primary);
        background: var(--color-background-secondary);
        font-weight: 600;
      }
      td {
        color: var(--color-text-secondary);
      }
      blockquote, .explanation, .note, [data-block="explanation"] {
        margin: 10px 0;
        padding: 10px 12px;
        border-left: 3px solid #378add;
        border-radius: 8px;
        background: rgba(55, 138, 221, 0.1);
      }
    </style>`;
}

function withIframeShell(html: string, frameId: string): string {
    return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    ${wrapperStyles()}
  </head>
  <body>
    ${html}
    <script>
      if (!window.sendPrompt) {
        window.sendPrompt = function () { /* no-op in embedded renderer */ };
      }
    </script>
    ${bridgeScript(frameId)}
  </body>
</html>`;
}

function rewriteExternalChartJs(html: string): string {
    // Claude-style snippets often load Chart.js from CDN. Replace with local bundled URL
    // so rendering still works without network access.
    return html
        .replace(
            /<script[^>]+src=["']https?:\/\/[^"']*chart(?:\.min)?(?:\.umd)?\.js[^"']*["'][^>]*>\s*<\/script>/gi,
            `<script src="${LOCAL_CHART_JS_URL}"></script>`
        )
        .replace(
            /<script[^>]+src=["']https?:\/\/cdnjs\.cloudflare\.com\/ajax\/libs\/chart\.js\/[^"']*["'][^>]*>\s*<\/script>/gi,
            `<script src="${LOCAL_CHART_JS_URL}"></script>`
        );
}

function injectBridgeIntoFullDocument(html: string, frameId: string): string {
    const styled = /<\/head>/i.test(html)
        ? html.replace(/<\/head>/i, `${wrapperStyles()}</head>`)
        : html;
    return /<\/body>/i.test(styled)
        ? styled.replace(
            /<\/body>/i,
            `<script>if(!window.sendPrompt){window.sendPrompt=function(){}};</script>${bridgeScript(frameId)}</body>`
          )
        : `${styled}${bridgeScript(frameId)}`;
}

function toIframeSrcDoc(html: string, frameId: string): string {
    const rewritten = rewriteExternalChartJs(html);
    const trimmed = html.trim().toLowerCase();
    // If the model already returned a full document, render it directly.
    if (trimmed.startsWith("<!doctype") || trimmed.includes("<html")) {
        return injectBridgeIntoFullDocument(rewritten, frameId);
    }
    // Otherwise, wrap fragment HTML in a minimal shell.
    return withIframeShell(rewritten, frameId);
}

export default function VisualArtifactCard({ artifact }: Props) {
    const [iframeHeight, setIframeHeight] = useState(560);
    const frameId = useMemo(
        () => `artifact-${Math.random().toString(36).slice(2)}-${Date.now()}`,
        []
    );
    const srcDoc = useMemo(
        () => (artifact.type === "interactive_html" ? toIframeSrcDoc(artifact.code, frameId) : ""),
        [artifact, frameId]
    );
    const caption = (artifact.description ?? "").trim();
    const frameTitle = artifact.title.trim() || "Interactive chart";

    useEffect(() => {
        const onMessage = (event: MessageEvent) => {
            const data = event.data as { type?: string; frameId?: string; height?: number };
            if (data?.type !== "matopt_artifact_height" || data.frameId !== frameId) return;
            if (typeof data.height !== "number" || !Number.isFinite(data.height)) return;
            const next = Math.max(320, Math.min(2200, Math.ceil(data.height + 8)));
            setIframeHeight(next);
        };
        window.addEventListener("message", onMessage);
        return () => window.removeEventListener("message", onMessage);
    }, [frameId]);

    return (
        <section className="visual-card">
            {artifact.type === "svg" ? (
                <div
                    className="visual-card__svg"
                    dangerouslySetInnerHTML={{ __html: artifact.code }}
                />
            ) : artifact.type === "plotly" ? (
                <div className="visual-card__plotly">
                    <PlotRenderer json={artifact.code} />
                </div>
            ) : (
                <iframe
                    className="visual-card__iframe"
                    sandbox="allow-scripts allow-same-origin"
                    srcDoc={srcDoc}
                    title={frameTitle}
                    scrolling="no"
                    style={{ height: iframeHeight }}
                />
            )}
            {caption && <p className="visual-card__caption">{caption}</p>}
        </section>
    );
}

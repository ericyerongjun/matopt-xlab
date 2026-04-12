import type { PdfWorkflowResponseBody } from "./types";

export async function runPdfWorkflow(
    file: File,
    prompt: string,
    model?: string
): Promise<PdfWorkflowResponseBody> {
    const form = new FormData();
    form.append("file", file);
    form.append("prompt", prompt);
    if (model) {
        form.append("model", model);
    }

    const resp = await fetch("/api/workflows/pdf", {
        method: "POST",
        body: form,
    });

    if (!resp.ok) {
        let detail = `PDF workflow failed: ${resp.status}`;
        try {
            const parsed = (await resp.json()) as { detail?: string };
            if (parsed?.detail) detail = parsed.detail;
        } catch {
            const text = await resp.text();
            if (text) detail = text;
        }
        throw new Error(detail);
    }

    return (await resp.json()) as PdfWorkflowResponseBody;
}


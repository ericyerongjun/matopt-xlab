/**
 * Document service — upload and parse student files into LLM-friendly text.
 */

import apiClient from "./api";
import type { DocumentParseResult } from "../types/document";

export async function parseDocument(file: File): Promise<DocumentParseResult> {
    const form = new FormData();
    form.append("file", file);

    const { data } = await apiClient.post("/documents/parse", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300_000, // large documents may take a while
    });

    return {
        markdown: data.markdown,
        latexBlocks: data.latex_blocks ?? [],
        metadata: data.metadata,
        previewImageDataUrl: data.preview_image_data_url,
    };
}

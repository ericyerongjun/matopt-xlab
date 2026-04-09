/**
 * useDocument — handle document upload and parse results.
 */

import { useState, useCallback } from "react";
import { parseDocument } from "../services/document";
import type { DocumentParseResult } from "../types/document";

export function useDocument() {
    const [result, setResult] = useState<DocumentParseResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const upload = useCallback(
        async (file: File): Promise<DocumentParseResult | null> => {
            setLoading(true);
            setError(null);
            try {
                const parsed = await parseDocument(file);
                setResult(parsed);
                return parsed;
            } catch (err: unknown) {
                setError(
                    err instanceof Error ? err.message : "Document parse failed"
                );
                return null;
            } finally {
                setLoading(false);
            }
        },
        []
    );

    const clear = useCallback(() => {
        setResult(null);
        setError(null);
    }, []);

    return { result, loading, error, upload, clear };
}

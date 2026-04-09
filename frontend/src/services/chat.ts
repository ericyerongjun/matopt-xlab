/**
 * Chat service — send messages to the backend LLM.
 */

import apiClient from "./api";
import type { ChatRequestBody, ChatResponseBody } from "./types";

export async function sendChatMessage(
    body: ChatRequestBody
): Promise<ChatResponseBody> {
    const { data } = await apiClient.post<ChatResponseBody>("/chat", body);
    return data;
}

/**
 * Stream chat via SSE.
 *
 * TODO: Implement proper EventSource / fetch-based SSE reader here.
 * For now, falls back to the non-streaming endpoint.
 */
export async function streamChatMessage(
    body: ChatRequestBody,
    onChunk: (text: string) => void
): Promise<void> {
    const resp = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...body, stream: true }),
    });

    if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Stream request failed: ${resp.status}`);
    }
    if (!resp.body) {
        throw new Error("Streaming response body is empty");
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const event of events) {
            const dataLine = event
                .split("\n")
                .find((line) => line.startsWith("data: "));
            if (!dataLine) continue;

            const payload = dataLine.slice(6).trim();
            if (!payload || payload === "[DONE]") continue;

            let parsed: { delta?: string; error?: string } = {};
            try {
                parsed = JSON.parse(payload);
            } catch {
                continue;
            }

            if (parsed.error) {
                throw new Error(parsed.error);
            }
            if (parsed.delta) {
                onChunk(parsed.delta);
            }
        }
    }
}

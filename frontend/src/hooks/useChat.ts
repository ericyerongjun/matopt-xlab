/**
 * useChat — manages multi-conversation chat state (ChatGPT-style).
 *
 * Each conversation gets its own message thread. The hook exposes the
 * active conversation, a conversation list for the sidebar, and helpers
 * to create / switch / delete conversations.
 */

import { useState, useCallback, useMemo } from "react";
import { streamChatMessage } from "../services/chat";
import type { Message } from "../types/message";
import type { Conversation } from "../types/conversation";

let _nextId = 1;
function uid(prefix = "msg"): string {
    return `${prefix}-${_nextId++}-${Date.now()}`;
}

function titleFromContent(content: string): string {
    const cleaned = content.replace(/\$[^$]*\$/g, "math").replace(/\s+/g, " ");
    return cleaned.length > 40 ? cleaned.slice(0, 40) + "…" : cleaned;
}

function recoverStructuredAssistantPayload(raw: string): {
    content: string;
    artifacts?: Message["artifacts"];
    toolCalls?: Message["toolCalls"];
} {
    const trimmed = raw.trim();
    if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) {
        return { content: raw };
    }

    try {
        const parsed = JSON.parse(trimmed) as {
            assistant_markdown?: unknown;
            artifacts?: unknown;
            tool_calls?: unknown;
        };
        const maybeContent =
            typeof parsed.assistant_markdown === "string"
                ? parsed.assistant_markdown
                : raw;
        const artifacts = Array.isArray(parsed.artifacts)
            ? (parsed.artifacts as Message["artifacts"])
            : undefined;
        const toolCalls = Array.isArray(parsed.tool_calls)
            ? (parsed.tool_calls as Message["toolCalls"])
            : undefined;
        return { content: maybeContent, artifacts, toolCalls };
    } catch {
        return { content: raw };
    }
}

export function useChat() {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [activeId, setActiveId] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const activeConversation = useMemo(
        () => conversations.find((c) => c.id === activeId) ?? null,
        [conversations, activeId]
    );

    const messages = activeConversation?.messages ?? [];

    // ── helpers ─────────────────────────────────────────────────────────

    const createConversation = useCallback((): string => {
        const id = uid("conv");
        const conv: Conversation = {
            id,
            title: "New chat",
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
        };
        setConversations((prev) => [conv, ...prev]);
        setActiveId(id);
        setError(null);
        return id;
    }, []);

    const switchConversation = useCallback((id: string) => {
        setActiveId(id);
        setError(null);
    }, []);

    const deleteConversation = useCallback(
        (id: string) => {
            setConversations((prev) => prev.filter((c) => c.id !== id));
            if (activeId === id) {
                setActiveId(null);
            }
        },
        [activeId]
    );

    const renameConversation = useCallback((id: string, title: string) => {
        setConversations((prev) =>
            prev.map((c) => (c.id === id ? { ...c, title } : c))
        );
    }, []);

    const runAssistantForHistory = useCallback(
        async (
            convId: string,
            history: Array<{ role: Message["role"]; content: string }>,
            model?: string
        ) => {
            const assistantId = uid("asst");
            const assistantMsg: Message = {
                id: assistantId,
                role: "assistant",
                content: "",
                timestamp: Date.now(),
            };

            setConversations((prev) =>
                prev.map((c) =>
                    c.id === convId
                        ? {
                              ...c,
                              messages: [...c.messages, assistantMsg],
                              updatedAt: Date.now(),
                          }
                        : c
                )
            );

            await streamChatMessage(
                {
                    messages: history.map((m) => ({
                        role: m.role,
                        content: m.content,
                    })),
                    model,
                    agentic: true,
                },
                (delta) => {
                    setConversations((prev) =>
                        prev.map((c) => {
                            if (c.id !== convId) return c;
                            return {
                                ...c,
                                messages: c.messages.map((m) =>
                                    m.id === assistantId
                                        ? { ...m, content: m.content + delta }
                                        : m
                                ),
                                updatedAt: Date.now(),
                            };
                        })
                    );
                },
                (done) => {
                    setConversations((prev) =>
                        prev.map((c) => {
                            if (c.id !== convId) return c;
                            return {
                                ...c,
                                messages: c.messages.map((m) =>
                                    m.id === assistantId
                                        ? (() => {
                                              const recovered = recoverStructuredAssistantPayload(m.content);
                                              const mappedToolCalls = done.tool_calls?.map((call) => ({
                                                  name: call.name,
                                                  arguments: call.arguments,
                                                  result: call.result,
                                              }));
                                              return {
                                                  ...m,
                                                  content: recovered.content,
                                                  toolCalls: mappedToolCalls ?? recovered.toolCalls,
                                                  artifacts: done.artifacts ?? recovered.artifacts,
                                                  metadata: done.metadata,
                                              };
                                          })()
                                        : m
                                ),
                                updatedAt: Date.now(),
                            };
                        })
                    );
                }
            );
        },
        []
    );

    // ── send message ────────────────────────────────────────────────────

    const sendMessage = useCallback(
        async (content: string, model?: string) => {
            let convId = activeId;

            // Auto-create conversation if none active
            if (!convId) {
                convId = uid("conv");
                const conv: Conversation = {
                    id: convId,
                    title: titleFromContent(content),
                    messages: [],
                    createdAt: Date.now(),
                    updatedAt: Date.now(),
                };
                setConversations((prev) => [conv, ...prev]);
                setActiveId(convId);
            }

            const userMsg: Message = {
                id: uid(),
                role: "user",
                content,
                timestamp: Date.now(),
            };

            // Append user message & update title if first message
            setConversations((prev) =>
                prev.map((c) => {
                    if (c.id !== convId) return c;
                    const isFirst = c.messages.length === 0;
                    return {
                        ...c,
                        title: isFirst ? titleFromContent(content) : c.title,
                        messages: [...c.messages, userMsg],
                        updatedAt: Date.now(),
                    };
                })
            );

            setLoading(true);
            setError(null);

            try {
                // Build history from the current conversation
                const currentConv = conversations.find(
                    (c) => c.id === convId
                );
                const history = [
                    ...(currentConv?.messages ?? []),
                    userMsg,
                ];

                await runAssistantForHistory(convId, history, model);
            } catch (err: unknown) {
                const msg =
                    err instanceof Error ? err.message : "Chat failed";
                setError(msg);
            } finally {
                setLoading(false);
            }
        },
        [activeId, conversations, runAssistantForHistory]
    );

    const regenerateAssistant = useCallback(
        async (assistantId: string, model?: string) => {
            if (!activeId) return;
            const conv = conversations.find((c) => c.id === activeId);
            if (!conv) return;

            const asstIdx = conv.messages.findIndex(
                (m) => m.id === assistantId && m.role === "assistant"
            );
            if (asstIdx < 0) return;

            let userIdx = -1;
            for (let i = asstIdx - 1; i >= 0; i -= 1) {
                if (conv.messages[i].role === "user") {
                    userIdx = i;
                    break;
                }
            }
            if (userIdx < 0) return;

            const historyMessages = conv.messages
                .slice(0, userIdx + 1)
                .map((m) => ({ role: m.role, content: m.content }));

            setConversations((prev) =>
                prev.map((c) =>
                    c.id === activeId
                        ? {
                              ...c,
                              messages: c.messages.slice(0, userIdx + 1),
                              updatedAt: Date.now(),
                          }
                        : c
                )
            );

            setLoading(true);
            setError(null);
            try {
                await runAssistantForHistory(activeId, historyMessages, model);
            } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : "Regenerate failed";
                setError(msg);
            } finally {
                setLoading(false);
            }
        },
        [activeId, conversations, runAssistantForHistory]
    );

    const clearChat = useCallback(() => {
        if (!activeId) return;
        setConversations((prev) =>
            prev.map((c) =>
                c.id === activeId ? { ...c, messages: [], updatedAt: Date.now() } : c
            )
        );
        setError(null);
    }, [activeId]);

    return {
        // Conversation list (for sidebar)
        conversations,
        activeId,
        createConversation,
        switchConversation,
        deleteConversation,
        renameConversation,
        // Active chat
        messages,
        loading,
        error,
        sendMessage,
        regenerateAssistant,
        clearChat,
    };
}

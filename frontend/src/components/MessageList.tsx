/**
 * MessageList — ChatGPT-style message thread with streamed assistant rendering.
 */

import React, { useEffect, useRef, useState } from "react";
import type { Message } from "../types/message";
import MarkdownRenderer from "./MarkdownRenderer";
import VisualArtifactCard from "./VisualArtifactCard";

interface Props {
    messages: Message[];
    loading?: boolean;
    onRegenerate?: (assistantId: string) => void;
}

interface MessageRowProps {
    msg: Message;
    loading?: boolean;
    onRegenerate?: (assistantId: string) => void;
    showActions?: boolean;
}

function looksLikeRawBackendMaterial(content: string): boolean {
    const raw = content.trim();
    if (!raw) return false;
    const lower = raw.toLowerCase();
    if (
        raw.startsWith("{") &&
        (raw.includes("\"assistant_markdown\"") || raw.includes("\"artifacts\"") || raw.includes("\"tool_calls\""))
    ) {
        return true;
    }
    return (
        lower.includes("traceback (most recent call last):") ||
        lower.includes("syntaxerror:") ||
        lower.includes("import plotly.graph_objects") ||
        lower.includes("fig.show()")
    );
}

function MessageRow({ msg, loading, onRegenerate, showActions }: MessageRowProps) {
    const hideRaw = msg.role === "assistant" && looksLikeRawBackendMaterial(msg.content);
    const [copied, setCopied] = useState(false);

    const copyOutput = async () => {
        try {
            await navigator.clipboard.writeText(msg.content || "");
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1200);
        } catch {
            setCopied(false);
        }
    };

    return (
        <div
            className={`thread__row ${msg.role === "user"
                ? "thread__row--user"
                : "thread__row--assistant"
                }`}
        >
            <div className="thread__message">
                <div className="thread__content">
                    <div className="thread__body">
                        {msg.role === "assistant" ? (
                            <>
                                {!hideRaw && <MarkdownRenderer content={msg.content} />}
                                {msg.artifacts && msg.artifacts.length > 0 && (
                                    <div className="thread__artifacts">
                                        {msg.artifacts.map((artifact, idx) => (
                                            <VisualArtifactCard
                                                key={`${msg.id}-artifact-${idx}`}
                                                artifact={artifact}
                                            />
                                        ))}
                                    </div>
                                )}
                                {showActions && (
                                    <div className="thread__message-actions">
                                        <button
                                            type="button"
                                            className="thread__message-action"
                                            onClick={copyOutput}
                                        >
                                            {copied ? "Copied" : "Copy"}
                                        </button>
                                        <button
                                            type="button"
                                            className="thread__message-action"
                                            onClick={() => onRegenerate?.(msg.id)}
                                            disabled={Boolean(loading)}
                                        >
                                            Regenerate
                                        </button>
                                    </div>
                                )}
                            </>
                        ) : (
                            <p>{msg.content}</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function MessageList({ messages, loading, onRegenerate }: Props) {
    const bottomRef = useRef<HTMLDivElement>(null);
    const [loadingElapsedMs, setLoadingElapsedMs] = useState(0);
    const latestAssistant = [...messages].reverse().find((m) => m.role === "assistant");
    const streamingId = loading && latestAssistant ? latestAssistant.id : null;
    const showLoadingRow = loading && (!latestAssistant || !latestAssistant.content);
    const showBreathingDot = showLoadingRow && loadingElapsedMs < 1200;

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading, streamingId]);

    useEffect(() => {
        if (!showLoadingRow) {
            setLoadingElapsedMs(0);
            return;
        }

        const startedAt = Date.now();
        const timer = window.setInterval(() => {
            setLoadingElapsedMs(Date.now() - startedAt);
        }, 80);

        return () => window.clearInterval(timer);
    }, [showLoadingRow]);

    if (messages.length === 0 && !loading) {
        return null;
    }

    return (
        <div className="thread">
            {messages.map((msg) => {
                return (
                    <MessageRow
                        key={msg.id}
                        msg={msg}
                        loading={loading}
                        onRegenerate={onRegenerate}
                        showActions={
                            msg.role === "assistant"
                            && !!msg.content.trim()
                            && !(loading && msg.id === streamingId)
                        }
                    />
                );
            })}

            {showLoadingRow && (
                <div className="thread__row thread__row--assistant">
                    <div className="thread__message">
                        <div className="thread__content">
                            <div className="thread__body">
                                {showBreathingDot ? (
                                    <div className="thread__thinking-dot-wrap" aria-label="Thinking">
                                        <span className="thread__thinking-dot" />
                                    </div>
                                ) : (
                                    <div className="thread__thinking-status" aria-label="Thinking status">
                                        <span className="thread__thinking-status-text">Thinking</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <div ref={bottomRef} />
        </div>
    );
}

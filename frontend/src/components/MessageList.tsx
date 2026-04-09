/**
 * MessageList — ChatGPT-style message thread with streamed assistant rendering.
 */

import React, { useEffect, useRef, useState } from "react";
import type { Message } from "../types/message";
import MarkdownRenderer from "./MarkdownRenderer";

interface Props {
    messages: Message[];
    loading?: boolean;
}

interface MessageRowProps {
    msg: Message;
}

function MessageRow({ msg }: MessageRowProps) {
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
                                <MarkdownRenderer content={msg.content} />
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

export default function MessageList({ messages, loading }: Props) {
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
                                        <span className="thread__thinking-status-chevron" aria-hidden="true">
                                            ›
                                        </span>
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

/** Roles for chat messages. */
export type MessageRole = "user" | "assistant" | "system";

export interface VisualArtifact {
    type: "svg" | "interactive_html" | "plotly";
    title: string;
    description?: string;
    code: string;
}

/** A single chat message. */
export interface Message {
    id: string;
    role: MessageRole;
    content: string;
    timestamp: number;
    /** Tool calls made during this message (assistant only). */
    toolCalls?: ToolCall[];
    artifacts?: VisualArtifact[];
    metadata?: Record<string, unknown>;
}

export interface ToolCall {
    name: string;
    arguments: Record<string, unknown>;
    result?: string;
}

/** Shared API type definitions. */

export interface ChatRequestBody {
    messages: { role: string; content: string }[];
    model?: string;
    stream?: boolean;
    agentic?: boolean;
    skill_slugs?: string[];
    use_sympy?: boolean;
    use_wolfram?: boolean;
}

export interface VisualArtifact {
    type: "svg" | "interactive_html" | "plotly";
    title: string;
    description?: string;
    code: string;
}

export interface ChatResponseBody {
    id: string;
    content: string;
    tool_calls?: { name: string; arguments: Record<string, unknown>; result?: string }[];
    artifacts?: VisualArtifact[];
    metadata?: Record<string, unknown>;
    usage?: Record<string, number>;
}

export interface StreamDonePayload {
    done: boolean;
    id: string;
    artifacts?: VisualArtifact[];
    tool_calls?: { name: string; arguments: Record<string, unknown>; result?: string }[];
    metadata?: Record<string, unknown>;
    usage?: Record<string, number>;
}

export interface OcrResponseBody {
    latex: string;
    confidence: number;
    sympy_valid: boolean;
    canonical_latex: string | null;
}

export interface MathRequestBody {
    latex: string;
    variable?: string;
    order?: number;
    lower?: string;
    upper?: string;
    substitutions?: Record<string, number>;
}

export interface MathResponseBody {
    success: boolean;
    result: string;
    error?: string;
}

export interface SuggestionResponseBody {
    suggestions: string[];
}

export interface FollowUpRequestBody {
    content: string;
    count?: number;
}

export interface FollowUpResponseBody {
    followups: string[];
}

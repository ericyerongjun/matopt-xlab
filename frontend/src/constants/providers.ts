export const PROVIDER_MODELS: Record<string, string[]> = {
    ChatGPT: ["GPT-4o", "GPT-5.4"],
    DeepSeek: ["DeepSeek-V3", "DeepSeek-R1"],
    Qwen: ["Qwen2.5-72B", "Qwen-Max"],
    Kimi: ["Kimi K2", "Kimi 1.5"],
    Llama: ["Llama 3.1 70B", "Llama 4 Maverick"],
    Gemini: ["Gemini 2.5 Pro", "Gemini 2.5 Flash"],
    "Tencent Hunyuan": ["Hunyuan Turbo", "Hunyuan T1"],
};

// Simple Icons CDN SVG endpoints (brand marks).
// We use monochrome white logos for dark UI.
export const PROVIDER_LOGOS: Record<string, string> = {
    ChatGPT: "https://cdn.simpleicons.org/openai/FFFFFF",
    DeepSeek: "https://cdn.simpleicons.org/deepseek/FFFFFF",
    Qwen: "https://cdn.simpleicons.org/qwen/FFFFFF",
    Kimi: "https://cdn.simpleicons.org/moonshot/FFFFFF",
    Llama: "https://cdn.simpleicons.org/meta/FFFFFF",
    Gemini: "https://cdn.simpleicons.org/googlegemini/FFFFFF",
    "Tencent Hunyuan": "https://cdn.simpleicons.org/tencent/FFFFFF",
};

export const PROVIDER_INITIALS: Record<string, string> = {
    ChatGPT: "AI",
    DeepSeek: "DS",
    Qwen: "QW",
    Kimi: "KM",
    Llama: "LL",
    Gemini: "GM",
    "Tencent Hunyuan": "TH",
};

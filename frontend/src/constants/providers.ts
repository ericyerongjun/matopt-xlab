import openaiLogo from "@lobehub/icons-static-png/dark/openai.png";
import deepseekLogo from "@lobehub/icons-static-png/dark/deepseek-color.png";
import qwenLogo from "@lobehub/icons-static-png/dark/qwen-color.png";
import kimiLogo from "@lobehub/icons-static-png/dark/kimi-color.png";
import geminiLogo from "@lobehub/icons-static-png/dark/gemini-color.png";

export const PROVIDER_MODELS: Record<string, string[]> = {
    ChatGPT: ["GPT-4o", "GPT-5.4"],
    DeepSeek: ["DeepSeek-V3", "DeepSeek-R1"],
    Qwen: ["Qwen2.5-72B", "Qwen-Max"],
    Kimi: ["Kimi K2", "Kimi 1.5"],
    Llama: ["Llama 3.1 70B", "Llama 4 Maverick"],
    Gemini: ["Gemini 2.5 Pro", "Gemini 2.5 Flash"],
};

export const PROVIDER_LOGOS: Record<string, string> = {
    ChatGPT: openaiLogo,
    DeepSeek: deepseekLogo,
    Qwen: qwenLogo,
    Kimi: kimiLogo,
    Llama: "https://cdn.simpleicons.org/meta/FFFFFF",
    Gemini: geminiLogo,
};

export const DEFAULT_PROVIDER_LOGO = openaiLogo;

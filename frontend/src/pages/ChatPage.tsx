/**
 * ChatPage — ChatGPT-style layout: sidebar + main content area.
 *
 * Sidebar: conversation history, new-chat button, user section.
 * Main: centered message thread, welcome screen when empty,
 *       and a bottom-pinned input bar.
 */

import React, { useState, useCallback, useRef, useEffect } from "react";
import { ChevronDown, X } from "lucide-react";
import { useChat } from "../hooks/useChat";
import { useDocument } from "../hooks/useDocument";
import { useExport } from "../hooks/useExport";
import { MessageList, MathInput, Sidebar, WelcomeScreen } from "../components";
import type { ExportFormat } from "../types/export";
import {
    DEFAULT_PROVIDER_LOGO,
    PROVIDER_MODELS,
    PROVIDER_LOGOS,
} from "../constants/providers";

const ACCEPTED_EXTENSIONS = [
    ".pdf",
    ".pptx",
    ".ppt",
    ".doc",
    ".docx",
    ".r",
    ".rmd",
    ".py",
    ".ipynb",
    ".c",
    ".cpp",
    ".java",
    ".png",
    ".jpg",
    ".jpeg",
    ".heic",
];

const TEXT_PREVIEW_EXTENSIONS = new Set([
    "r",
    "rmd",
    "py",
    "ipynb",
    "c",
    "cpp",
    "java",
]);

function getExtension(filename: string): string {
    const parts = filename.toLowerCase().split(".");
    return parts.length > 1 ? parts[parts.length - 1] : "";
}

function isPdfFile(file: File): boolean {
    return (
        file.type === "application/pdf" || getExtension(file.name) === "pdf"
    );
}

function isImageFile(file: File): boolean {
    const ext = getExtension(file.name);
    return (
        file.type.startsWith("image/") ||
        ext === "png" ||
        ext === "jpg" ||
        ext === "jpeg" ||
        ext === "heic"
    );
}

function isTextPreviewFile(file: File): boolean {
    return TEXT_PREVIEW_EXTENSIONS.has(getExtension(file.name));
}

function toApiModelName(selectedModel: string): string {
    const normalized = selectedModel.trim().toLowerCase();
    if (normalized === "gpt-5.4") return "gpt-5.4";
    if (normalized === "gpt-4o") return "gpt-4o";
    if (normalized === "deepseek-v3") return "deepseek-chat";
    if (normalized === "deepseek-r1") return "deepseek-reasoner";
    return selectedModel;
}

function maybeRevokeObjectUrl(url: string | null): void {
    if (url?.startsWith("blob:")) {
        URL.revokeObjectURL(url);
    }
}

export default function ChatPage() {
    const {
        conversations,
        activeId,
        createConversation,
        switchConversation,
        deleteConversation,
        messages,
        loading,
        error,
        sendMessage,
        regenerateAssistant,
    } = useChat();

    const {
        upload: uploadDoc,
        loading: docLoading,
        error: docError,
    } = useDocument();
    const { doExport, loading: exportLoading } = useExport();
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [modelMenuOpen, setModelMenuOpen] = useState(false);
    const [selectedProvider, setSelectedProvider] = useState("ChatGPT");
    const [selectedModel, setSelectedModel] = useState("GPT-4o");
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [textPreview, setTextPreview] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const modelMenuRef = useRef<HTMLDivElement>(null);

    const handleNewChat = useCallback(() => {
        createConversation();
    }, [createConversation]);

    const handleSend = useCallback(
        (text: string) => {
            const attachment = uploadedFile;
            sendMessage(text, toApiModelName(selectedModel), attachment);
            if (attachment) {
                setUploadedFile(null);
                setTextPreview(null);
                setPreviewUrl((prev) => {
                    maybeRevokeObjectUrl(prev);
                    return null;
                });
            }
        },
        [sendMessage, selectedModel, uploadedFile]
    );

    const handleRegenerate = useCallback(
        (assistantId: string) => {
            regenerateAssistant(assistantId, toApiModelName(selectedModel));
        },
        [regenerateAssistant, selectedModel]
    );

    useEffect(() => {
        const handleOutsideClick = (event: MouseEvent) => {
            if (!modelMenuRef.current) return;
            if (!modelMenuRef.current.contains(event.target as Node)) {
                setModelMenuOpen(false);
            }
        };
        document.addEventListener("mousedown", handleOutsideClick);
        return () => {
            document.removeEventListener("mousedown", handleOutsideClick);
        };
    }, []);

    useEffect(() => {
        return () => {
            maybeRevokeObjectUrl(previewUrl);
        };
    }, [previewUrl]);

    const handleFileClick = useCallback(() => {
        fileInputRef.current?.click();
    }, []);

    const handleFileChange = useCallback(
        async (e: React.ChangeEvent<HTMLInputElement>) => {
            const file = e.target.files?.[0];
            if (file) {
                setUploadedFile(file);
                setTextPreview(null);
                setPreviewUrl((prev) => {
                    maybeRevokeObjectUrl(prev);
                    return isPdfFile(file) || isImageFile(file)
                        ? URL.createObjectURL(file)
                        : null;
                });

                if (isTextPreviewFile(file)) {
                    try {
                        const raw = await file.text();
                        const lines = raw.split(/\r?\n/).slice(0, 32);
                        setTextPreview(lines.join("\n"));
                    } catch {
                        setTextPreview("Unable to preview this text file.");
                    }
                }

                const parsed = await uploadDoc(file);
                if (parsed?.previewImageDataUrl) {
                    setPreviewUrl((prev) => {
                        maybeRevokeObjectUrl(prev);
                        return parsed.previewImageDataUrl ?? null;
                    });
                }
            }
            // Reset so the same file can be re-selected
            if (fileInputRef.current) fileInputRef.current.value = "";
        },
        [uploadDoc]
    );

    const handleRemoveFile = useCallback(() => {
        setUploadedFile(null);
        setTextPreview(null);
        setPreviewUrl((prev) => {
            maybeRevokeObjectUrl(prev);
            return null;
        });
    }, []);

    const handleExport = useCallback(
        (format: ExportFormat) => {
            const allContent = messages
                .map((m) =>
                    m.role === "user" ? `**You:** ${m.content}` : m.content
                )
                .join("\n\n---\n\n");
            doExport(allContent, format, "MatOpt Chat Export");
        },
        [messages, doExport]
    );

    const isEmpty = messages.length === 0;

    return (
        <div className="app-layout">
            <Sidebar
                conversations={conversations}
                activeId={activeId}
                onNewChat={handleNewChat}
                onSelect={switchConversation}
                onDelete={deleteConversation}
                onExport={handleExport}
                selectedProvider={selectedProvider}
                collapsed={sidebarCollapsed}
                onToggleCollapse={() =>
                    setSidebarCollapsed(!sidebarCollapsed)
                }
            />

            <main className="main">
                {/* Header bar */}
                <header className="main__header">
                    <div className="main__header-left" ref={modelMenuRef}>
                        <button
                            className="main__model-button"
                            type="button"
                            onClick={() => setModelMenuOpen(!modelMenuOpen)}
                        >
                            <span className="main__model-provider">
                                <img
                                    className="main__provider-logo"
                                    src={PROVIDER_LOGOS[selectedProvider] ?? DEFAULT_PROVIDER_LOGO}
                                    alt={`${selectedProvider} logo`}
                                    onError={(e) => {
                                        e.currentTarget.src = DEFAULT_PROVIDER_LOGO;
                                    }}
                                />
                                {selectedProvider}
                            </span>
                            <span className="main__model-selected">
                                {selectedModel}
                            </span>
                            <ChevronDown size={16} />
                        </button>
                        {modelMenuOpen && (
                            <div className="main__model-menu">
                                {Object.entries(PROVIDER_MODELS).map(
                                    ([provider, models]) => (
                                        <div
                                            key={provider}
                                            className="main__model-group"
                                        >
                                            <button
                                                className={`main__provider-item ${selectedProvider === provider
                                                    ? "main__provider-item--active"
                                                    : ""
                                                    }`}
                                                type="button"
                                                onClick={() => {
                                                    setSelectedProvider(
                                                        provider
                                                    );
                                                    if (
                                                        !models.includes(
                                                            selectedModel
                                                        )
                                                    ) {
                                                        setSelectedModel(
                                                            models[0]
                                                        );
                                                    }
                                                }}
                                            >
                                                <span className="main__provider-logo-wrap">
                                                    <img
                                                        className="main__provider-logo"
                                                        src={PROVIDER_LOGOS[provider] ?? DEFAULT_PROVIDER_LOGO}
                                                        alt={`${provider} logo`}
                                                        onError={(e) => {
                                                            e.currentTarget.src = DEFAULT_PROVIDER_LOGO;
                                                        }}
                                                    />
                                                </span>
                                                {provider}
                                            </button>
                                            {selectedProvider === provider && (
                                                <div className="main__model-suboptions">
                                                    {models.map((model) => (
                                                        <button
                                                            key={model}
                                                            className={`main__model-item ${selectedModel === model
                                                                ? "main__model-item--active"
                                                                : ""
                                                                }`}
                                                            type="button"
                                                            onClick={() => {
                                                                setSelectedProvider(
                                                                    provider
                                                                );
                                                                setSelectedModel(
                                                                    model
                                                                );
                                                                setModelMenuOpen(
                                                                    false
                                                                );
                                                            }}
                                                        >
                                                            {model}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )
                                )}
                            </div>
                        )}
                    </div>

                </header>

                {/* Message area */}
                <div className="main__thread-area">
                    {isEmpty ? (
                        <WelcomeScreen />
                    ) : (
                        <MessageList
                            messages={messages}
                            loading={loading}
                            onRegenerate={handleRegenerate}
                        />
                    )}
                </div>

                {/* Error banner */}
                {error && (
                    <div className="main__error">
                        <span>{error}</span>
                    </div>
                )}

                {/* Input bar */}
                <div className="main__input-area">
                    {uploadedFile && (
                        <div className="file-preview-card">
                            <div className="file-preview-card__header">
                                <div className="file-preview-card__meta">
                                    <span className="file-preview-card__name">
                                        {uploadedFile.name}
                                    </span>
                                    <span className="file-preview-card__sub">
                                        {docLoading
                                            ? "Analyzing file..."
                                            : "Front page preview"}
                                    </span>
                                </div>
                                <button
                                    type="button"
                                    className="file-preview-card__remove"
                                    onClick={handleRemoveFile}
                                    title="Remove file"
                                >
                                    <X size={14} />
                                </button>
                            </div>
                            {isPdfFile(uploadedFile) && previewUrl ? (
                                <iframe
                                    src={`${previewUrl}#page=1&toolbar=0&navpanes=0&scrollbar=0`}
                                    title="PDF front page preview"
                                    className="file-preview-card__pdf"
                                />
                            ) : ((isImageFile(uploadedFile) &&
                                  previewUrl) ||
                                  previewUrl?.startsWith("data:image/")) ? (
                                <img
                                    src={previewUrl}
                                    alt={`Preview of ${uploadedFile.name}`}
                                    className="file-preview-card__image"
                                />
                            ) : textPreview ? (
                                <pre className="file-preview-card__text">
                                    {textPreview}
                                </pre>
                            ) : (
                                <div className="file-preview-card__fallback">
                                    <span className="file-preview-card__fallback-title">
                                        {uploadedFile.name}
                                    </span>
                                    <span>
                                        Front-page thumbnail is not available
                                        for this file type yet.
                                    </span>
                                </div>
                            )}
                            {docError && (
                                <div className="file-preview-card__error">
                                    {docError}
                                </div>
                            )}
                        </div>
                    )}
                    <MathInput
                        onSubmit={handleSend}
                        onFileClick={handleFileClick}
                        disabled={loading}
                        loading={loading}
                    />
                </div>

                {/* Hidden file input */}
                <input
                    ref={fileInputRef}
                    type="file"
                    accept={ACCEPTED_EXTENSIONS.join(",")}
                    style={{ display: "none" }}
                    onChange={handleFileChange}
                />
            </main>
        </div>
    );
}

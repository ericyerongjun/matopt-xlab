/**
 * Sidebar — ChatGPT-style dark sidebar with conversation history.
 */

import React, { useState, useMemo, useRef, useEffect } from "react";
import {
    Plus,
    MessageSquare,
    Trash2,
    PanelLeftClose,
    PanelLeft,
    Search,
    X,
    NotebookPen,
    Lightbulb,
    ClipboardCheck,
    BrainCircuit,
    Grid2X2Plus,
} from "lucide-react";
import type { Conversation } from "../types/conversation";
import type { ExportFormat } from "../types/export";

interface Props {
    conversations: Conversation[];
    activeId: string | null;
    onNewChat: () => void;
    onSelect: (id: string) => void;
    onDelete: (id: string) => void;
    onExport?: (format: ExportFormat) => void;
    selectedProvider: string;
    collapsed: boolean;
    onToggleCollapse: () => void;
}

export default function Sidebar({
    conversations,
    activeId,
    onNewChat,
    onSelect,
    onDelete,
    selectedProvider,
    collapsed,
    onToggleCollapse,
}: Props) {
    const projectLogoUrl = "/assets/xlab.PNG";

    const featureButtons = [
        { label: "Generate Exercises", icon: NotebookPen },
        { label: "Solve & Explain", icon: Lightbulb },
        { label: "Mock Exam", icon: ClipboardCheck },
        { label: "Extract mindmap", icon: BrainCircuit },
        { label: "More app", icon: Grid2X2Plus },
    ];

    const [searchOpen, setSearchOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const searchInputRef = useRef<HTMLInputElement>(null);

    // Focus the search input when the search bar opens
    useEffect(() => {
        if (searchOpen) {
            searchInputRef.current?.focus();
        }
    }, [searchOpen]);

    // Filter conversations by search query
    const filtered = useMemo(() => {
        if (!searchQuery.trim()) return conversations;
        const q = searchQuery.toLowerCase();
        return conversations.filter((c) => c.title.toLowerCase().includes(q));
    }, [conversations, searchQuery]);

    // Group conversations by date
    const today = new Date();
    const todayStart = new Date(
        today.getFullYear(),
        today.getMonth(),
        today.getDate()
    ).getTime();
    const weekAgo = todayStart - 7 * 86400000;
    const monthAgo = todayStart - 30 * 86400000;

    const groups: { label: string; convs: Conversation[] }[] = [];
    const todayConvs = filtered.filter(
        (c) => c.updatedAt >= todayStart
    );
    const weekConvs = filtered.filter(
        (c) => c.updatedAt >= weekAgo && c.updatedAt < todayStart
    );
    const monthConvs = filtered.filter(
        (c) => c.updatedAt >= monthAgo && c.updatedAt < weekAgo
    );
    const olderConvs = filtered.filter(
        (c) => c.updatedAt < monthAgo
    );

    if (todayConvs.length) groups.push({ label: "Today", convs: todayConvs });
    if (weekConvs.length)
        groups.push({ label: "Previous 7 Days", convs: weekConvs });
    if (monthConvs.length)
        groups.push({ label: "Previous 30 Days", convs: monthConvs });
    if (olderConvs.length) groups.push({ label: "Older", convs: olderConvs });

    return (
        <nav className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
            {/* Top section */}
            <div className="sidebar__top">
                {!collapsed && (
                    <div className="sidebar__top-bar">
                        <div
                            className="sidebar__model-icon"
                            title={`${selectedProvider} selected`}
                        >
                            <img
                                className="sidebar__model-logo sidebar__model-logo--brand"
                                src={projectLogoUrl}
                                alt="Polyu X AI Lab logo"
                            />
                        </div>
                        <button
                            className="sidebar__toggle"
                            onClick={onToggleCollapse}
                            title={collapsed ? "Open sidebar" : "Close sidebar"}
                        >
                            {collapsed ? (
                                <PanelLeft size={20} />
                            ) : (
                                <PanelLeftClose size={20} />
                            )}
                        </button>
                    </div>
                )}
                {collapsed && (
                    <button
                        className="sidebar__toggle"
                        onClick={onToggleCollapse}
                        title={collapsed ? "Open sidebar" : "Close sidebar"}
                    >
                        {collapsed ? (
                            <PanelLeft size={20} />
                        ) : (
                            <PanelLeftClose size={20} />
                        )}
                    </button>
                )}

                {!collapsed && (
                    <button
                        className="sidebar__new-chat"
                        onClick={onNewChat}
                        title="New chat"
                    >
                        <Plus size={18} />
                        <span>New chat</span>
                    </button>
                )}
                {collapsed && (
                    <button
                        className="sidebar__new-chat sidebar__new-chat--icon"
                        onClick={onNewChat}
                        title="New chat"
                    >
                        <Plus size={20} />
                    </button>
                )}
            </div>

            {!collapsed && (
                <div className="sidebar__quick">
                    {searchOpen ? (
                        <div className="sidebar__search-bar">
                            <Search size={16} className="sidebar__search-icon" />
                            <input
                                ref={searchInputRef}
                                className="sidebar__search-input"
                                type="text"
                                placeholder="Search chats…"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                            <button
                                className="sidebar__search-close"
                                type="button"
                                onClick={() => {
                                    setSearchOpen(false);
                                    setSearchQuery("");
                                }}
                                title="Close search"
                            >
                                <X size={14} />
                            </button>
                        </div>
                    ) : (
                        <button
                            className="sidebar__quick-item"
                            type="button"
                            onClick={() => setSearchOpen(true)}
                        >
                            <Search size={16} />
                            <span>Search chats</span>
                        </button>
                    )}
                    {featureButtons.map(({ label, icon: Icon }) => (
                        <button
                            key={label}
                            className="sidebar__quick-item"
                            type="button"
                        >
                            <Icon size={16} />
                            <span>{label}</span>
                        </button>
                    ))}
                </div>
            )}

            {/* Conversation list */}
            {!collapsed && (
                <div className="sidebar__conversations">
                    <div className="sidebar__section-label">Your chats</div>
                    {groups.length === 0 && (
                        <div className="sidebar__empty">
                            No conversations yet
                        </div>
                    )}
                    {groups.map((group) => (
                        <div key={group.label} className="sidebar__group">
                            <div className="sidebar__group-label">
                                {group.label}
                            </div>
                            {group.convs.map((conv) => (
                                <div
                                    key={conv.id}
                                    className={`sidebar__item ${conv.id === activeId
                                        ? "sidebar__item--active"
                                        : ""
                                        }`}
                                    onClick={() => onSelect(conv.id)}
                                >
                                    <MessageSquare size={16} />
                                    <span className="sidebar__item-title">
                                        {conv.title}
                                    </span>
                                    <button
                                        className="sidebar__item-delete"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onDelete(conv.id);
                                        }}
                                        title="Delete"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    ))}
                </div>
            )}

            {!collapsed && (
                <div className="sidebar__bottom">
                    <button className="sidebar__account" type="button" title="Account">
                        <div className="sidebar__account-avatar">YR</div>
                        <div className="sidebar__account-info">
                            <div className="sidebar__account-name">YE RONGJUN</div>
                            <div className="sidebar__account-meta">
                                Student ID: 24127428D
                            </div>
                            <div className="sidebar__account-meta">
                                Department: DSAI
                            </div>
                        </div>
                    </button>
                </div>
            )}
            {collapsed && (
                <div className="sidebar__bottom sidebar__bottom--collapsed">
                    <button
                        className="sidebar__account sidebar__account--collapsed"
                        type="button"
                        title="YE RONGJUN • 24127428D • DSAI"
                    >
                        <div className="sidebar__account-avatar">YR</div>
                    </button>
                </div>
            )}
        </nav>
    );
}

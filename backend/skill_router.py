from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Set, Tuple

from skill_store import list_skills, read_skill, slugify

_CACHE: Dict[str, Tuple[str, Set[str]]] = {}
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "your",
    "into",
    "when",
    "then",
    "have",
    "will",
    "should",
    "can",
    "use",
    "using",
    "help",
    "create",
    "make",
    "build",
    "code",
    "file",
    "repo",
    "project",
}

_INTENT_BOOSTS = [
    (
        {"graph", "plot", "plotly", "chart", "svg", "interactive", "html", "visualize", "visual"},
        {"web-artifacts-builder", "imagegen", "algorithmic-art", "frontend-skill", "spreadsheet", "jupyter-notebook"},
    ),
    (
        {"pdf", "doc", "docx", "ppt", "pptx", "slide", "slides"},
        {"pdf", "doc", "docx", "pptx", "slides", "xlsx", "spreadsheet"},
    ),
    (
        {"test", "testing", "e2e", "playwright", "browser", "screenshot"},
        {"playwright", "playwright-interactive", "webapp-testing", "screenshot"},
    ),
]


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9][a-z0-9\-\+_\.]{2,}", text.lower())


def _extract_keywords(content: str, limit: int = 2500) -> Set[str]:
    selected_lines: List[str] = []
    for line in content.splitlines()[:80]:
        stripped = line.strip()
        if stripped.startswith(("#", "-", "*")) or len(stripped) <= 90:
            selected_lines.append(stripped)
    text = "\n".join(selected_lines)[:limit]
    tokens = _tokenize(text)
    return {t for t in tokens if len(t) >= 3 and t not in _STOPWORDS}


def _skill_keywords(slug: str) -> Set[str]:
    normalized = slugify(slug)
    skill = read_skill(normalized)
    stamp = str(skill.get("updated_at", ""))
    cached = _CACHE.get(normalized)
    if cached and cached[0] == stamp:
        return cached[1]

    title = str(skill.get("title", ""))
    content = str(skill.get("content", ""))
    slug_terms = [p for p in normalized.split("-") if len(p) >= 3]
    keywords = set(slug_terms)
    keywords.update(_extract_keywords(title))
    keywords.update(_extract_keywords(content))
    _CACHE[normalized] = (stamp, keywords)
    return keywords


def _latest_user_text(messages: List[Dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            return str(message["content"])
    return ""


def auto_select_skill_slugs(
    messages: List[Dict[str, str]],
    max_skills: int = 4,
    min_score: int = 6,
) -> List[str]:
    query = _latest_user_text(messages).strip().lower()
    if not query:
        return []

    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return []

    scored: List[Tuple[int, str]] = []
    for item in list_skills():
        slug = str(item.get("slug", "")).strip()
        if not slug:
            continue

        score = 0
        if slug in query:
            score += 10

        slug_parts = [p for p in slug.split("-") if len(p) >= 3 and p not in _STOPWORDS]
        for part in slug_parts:
            if part in query_tokens:
                score += 6

        keywords = _skill_keywords(slug)
        overlap = len(keywords.intersection(query_tokens))
        score += min(overlap, 5)

        for terms, boosted_slugs in _INTENT_BOOSTS:
            if query_tokens.intersection(terms) and slug in boosted_slugs:
                score += 10

        if score >= min_score:
            scored.append((score, slug))

    scored.sort(key=lambda row: (-row[0], row[1]))
    return [slug for _, slug in scored[:max_skills]]


def _excerpt(content: str, max_chars: int = 900) -> str:
    condensed = re.sub(r"\s+", " ", content).strip()
    return condensed[:max_chars]


def _extract_json_object(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def llm_select_skills(
    *,
    openai_client: Any,
    model: str,
    messages: List[Dict[str, str]],
    max_skills: int = 4,
) -> Dict[str, Any]:
    if not messages:
        return {
            "strategy": "llm",
            "selected_slugs": [],
            "explanation": "No user message was provided, so no skills were selected.",
            "confidence": 0.0,
            "per_skill_rationale": [],
        }

    latest_user = _latest_user_text(messages).strip()
    if not latest_user:
        return {
            "strategy": "llm",
            "selected_slugs": [],
            "explanation": "The latest user message was empty, so no skills were selected.",
            "confidence": 0.0,
            "per_skill_rationale": [],
        }

    skills = list_skills()
    if not skills:
        return {
            "strategy": "llm",
            "selected_slugs": [],
            "explanation": "No skills are available in the skills folder.",
            "confidence": 1.0,
            "per_skill_rationale": [],
        }

    catalog_lines: List[str] = []
    valid_slugs: Set[str] = set()
    for item in skills:
        slug = str(item.get("slug", "")).strip()
        if not slug:
            continue
        valid_slugs.add(slug)
        title = str(item.get("title", slug)).strip()
        try:
            full = read_skill(slug)
            snippet = _excerpt(str(full.get("content", "")))
        except Exception:
            snippet = ""
        catalog_lines.append(f"- slug: {slug}\n  title: {title}\n  excerpt: {snippet}")

    system_prompt = (
        "You are a skill routing engine. "
        "Choose the most relevant skills for the user's latest request.\n"
        "Output strict JSON only (no markdown fences) with schema:\n"
        "{\n"
        '  "selected_slugs": ["slug1", "slug2"],\n'
        '  "explanation": "detailed explanation that compares selected vs non-selected skills",\n'
        '  "per_skill_rationale": [{"slug": "slug1", "why": "..." }],\n'
        '  "confidence": 0.0\n'
        "}\n"
        f"Rules:\n"
        f"- Select at most {max_skills} skills.\n"
        "- selected_slugs must be unique and must come from the provided catalog.\n"
        "- If no skill is relevant, return an empty selected_slugs array and explain why.\n"
        "- explanation must be specific and actionable, not generic."
    )
    user_prompt = (
        f"Latest user request:\n{latest_user}\n\n"
        f"Available skills catalog:\n{chr(10).join(catalog_lines)}"
    )

    completion = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    raw = completion.choices[0].message.content or ""
    parsed = _extract_json_object(raw)

    requested = parsed.get("selected_slugs", [])
    selected: List[str] = []
    if isinstance(requested, list):
        for slug in requested:
            normalized = slugify(str(slug))
            if normalized in valid_slugs and normalized not in selected:
                selected.append(normalized)
            if len(selected) >= max_skills:
                break

    per_skill_rationale = parsed.get("per_skill_rationale", [])
    normalized_rationale: List[Dict[str, str]] = []
    if isinstance(per_skill_rationale, list):
        for row in per_skill_rationale:
            if not isinstance(row, dict):
                continue
            slug = slugify(str(row.get("slug", "")))
            if slug not in selected:
                continue
            why = str(row.get("why", "")).strip()
            if not why:
                continue
            normalized_rationale.append({"slug": slug, "why": why})

    explanation = str(parsed.get("explanation", "")).strip()
    if not explanation:
        explanation = (
            "The router selected skills that best match the user request based on each SKILL.md scope."
        )

    confidence_raw = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except Exception:
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return {
        "strategy": "llm",
        "selected_slugs": selected,
        "explanation": explanation,
        "confidence": confidence,
        "per_skill_rationale": normalized_rationale,
    }


def resolve_skill_selection(
    messages: List[Dict[str, str]],
    explicit_skill_slugs: List[str] | None = None,
    openai_client: Any | None = None,
    model: str | None = None,
    max_skills: int = 4,
) -> Dict[str, Any]:
    if explicit_skill_slugs:
        normalized = [slugify(s) for s in explicit_skill_slugs if str(s).strip()]
        selected = list(dict.fromkeys(normalized))
        return {
            "strategy": "explicit",
            "selected_slugs": selected,
            "explanation": (
                "Skills were explicitly provided by the caller, so automatic routing was skipped."
            ),
            "confidence": 1.0,
            "per_skill_rationale": [],
        }

    if openai_client is not None and model:
        try:
            return llm_select_skills(
                openai_client=openai_client,
                model=model,
                messages=messages,
                max_skills=max_skills,
            )
        except Exception:
            # Fall back to deterministic routing when LLM selection fails.
            pass

    fallback = auto_select_skill_slugs(messages=messages, max_skills=max_skills)
    return {
        "strategy": "heuristic_fallback",
        "selected_slugs": fallback,
        "explanation": (
            "LLM skill selection was unavailable, so the router used keyword-intent fallback scoring."
        ),
        "confidence": 0.35,
        "per_skill_rationale": [],
    }

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SKILLS_ROOT = Path(__file__).resolve().parent / "skills"


def ensure_skills_root() -> Path:
    SKILLS_ROOT.mkdir(parents=True, exist_ok=True)
    return SKILLS_ROOT


def slugify(name: str) -> str:
    lowered = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "untitled-skill"


def _skill_path(slug: str) -> Path:
    safe = slugify(slug)
    return ensure_skills_root() / safe / "SKILL.md"


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            if title:
                return title
    return fallback


def list_skills() -> List[Dict[str, Any]]:
    root = ensure_skills_root()
    results: List[Dict[str, Any]] = []

    for skill_md in sorted(root.glob("*/SKILL.md")):
        slug = skill_md.parent.name
        stat = skill_md.stat()
        content = skill_md.read_text(encoding="utf-8")
        title = _extract_title(content, fallback=slug.replace("-", " ").title())
        results.append(
            {
                "slug": slug,
                "title": title,
                "path": str(skill_md),
                "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "size_bytes": stat.st_size,
            }
        )

    return results


def read_skill(slug: str) -> Dict[str, Any]:
    path = _skill_path(slug)
    if not path.exists():
        raise FileNotFoundError(f"Skill '{slug}' does not exist")

    content = path.read_text(encoding="utf-8")
    stat = path.stat()
    return {
        "slug": path.parent.name,
        "title": _extract_title(content, fallback=path.parent.name.replace("-", " ").title()),
        "content": content,
        "path": str(path),
        "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "size_bytes": stat.st_size,
    }


def upsert_skill(slug: str, content: str, title: str | None = None) -> Dict[str, Any]:
    normalized_slug = slugify(slug)
    safe_title = (title or normalized_slug.replace("-", " ").title()).strip()
    path = _skill_path(normalized_slug)
    path.parent.mkdir(parents=True, exist_ok=True)

    final_content = content.strip()
    if not final_content:
        final_content = f"# {safe_title}\n\nDescribe what this skill does.\n"
    elif not final_content.lstrip().startswith("# "):
        final_content = f"# {safe_title}\n\n{final_content}\n"
    else:
        final_content = f"{final_content}\n"

    path.write_text(final_content, encoding="utf-8")
    return read_skill(normalized_slug)


def delete_skill(slug: str) -> bool:
    path = _skill_path(slug)
    if not path.exists():
        return False

    path.unlink()
    # Keep directories tidy when empty.
    try:
        path.parent.rmdir()
    except OSError:
        pass
    return True

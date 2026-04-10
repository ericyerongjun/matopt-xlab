from __future__ import annotations

from skill_store import list_skills, read_skill, upsert_skill
from visual_tools import (
    create_interactive_html_scaffold,
    create_svg_scaffold,
    sanitize_interactive_html,
    validate_svg,
)

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "The 'mcp' package is required to run the MatOpt MCP server."
    ) from exc


mcp = FastMCP("matopt-visual-mcp")


@mcp.tool()
def scaffold_svg_graph(title: str, x_label: str = "X", y_label: str = "Y") -> str:
    """Create an SVG graph scaffold."""
    return create_svg_scaffold(title=title, x_label=x_label, y_label=y_label)


@mcp.tool()
def scaffold_interactive_graph(title: str) -> str:
    """Create an interactive HTML scaffold for charts."""
    return create_interactive_html_scaffold(title=title)


@mcp.tool()
def check_svg(svg_code: str) -> str:
    """Validate SVG code and return a status string."""
    result = validate_svg(svg_code)
    if result.get("ok") == "true":
        return "ok"
    return result.get("error", "invalid svg")


@mcp.tool()
def sanitize_html_visual(html_code: str) -> str:
    """Remove remote script/style dependencies from interactive HTML."""
    return sanitize_interactive_html(html_code)


@mcp.tool()
def list_skill_docs() -> str:
    """List SKILL.md documents managed by MatOpt."""
    return str(list_skills())


@mcp.tool()
def read_skill_doc(slug: str) -> str:
    """Read a SKILL.md document by slug."""
    return str(read_skill(slug))


@mcp.tool()
def write_skill_doc(slug: str, content: str, title: str = "") -> str:
    """Create or update a SKILL.md document."""
    return str(upsert_skill(slug=slug, content=content, title=title or None))


if __name__ == "__main__":
    mcp.run()

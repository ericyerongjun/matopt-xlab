from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from openai import OpenAI

from skill_store import read_skill
from visual_tools import (
    sanitize_interactive_html,
)

try:  # Optional at runtime, required for full agentic mode.
    from langchain_core.documents import Document
    from langchain_openai import ChatOpenAI
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover
    Document = None  # type: ignore[assignment]
    LANGGRAPH_AVAILABLE = False


class AgentRunState(TypedDict, total=False):
    messages: List[Dict[str, str]]
    model: str
    api_key: str
    skills: List[Dict[str, Any]]
    linked_skill_context: str
    plan: str
    raw_output: str
    result: Dict[str, Any]


_GRAPH = None


VISUAL_JSON_INSTRUCTION = """
Return strict JSON only (no markdown fences) with this schema:
{
  "assistant_markdown": "string",
  "artifacts": [
    {
      "type": "interactive_html | plotly",
      "title": "string",
      "description": "string",
      "code": "string"
    }
  ],
  "tool_calls": [
    {
      "name": "string",
      "arguments": {}
    }
  ]
}

When the user asks for graphs/visuals, always include at least one artifact.
Never return SVG artifacts.
Prefer Plotly artifacts unless the user explicitly asks for an interactive HTML chart.
For graph artifacts, keep title as an empty string and put short explanatory text in description.
"""

EDUCATION_STYLE_INSTRUCTION = """
Teaching style requirements:
- Default to education-oriented explanations.
- Explain concepts step by step with clear sequencing.
- Prefer concrete examples and intuition when possible.
- When a graph can improve understanding, include an appropriate visual artifact.
- End with an open-ended prompt that guides deeper learning (for example a follow-up question or offer to explain further).
"""


def _extract_json_block(raw: str) -> Dict[str, Any]:
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

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Fallback into plain markdown response.
    return {"assistant_markdown": raw, "artifacts": [], "tool_calls": []}


def _extract_python_code(raw: str) -> str:
    text = raw.strip()
    fenced = re.search(r"```python\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:python)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_panel_count(user_text: str) -> int:
    lower = user_text.lower()
    m = re.search(r"\b(\d+)\s*(?:graphs?|plots?|charts?)\b", lower)
    if m:
        try:
            n = int(m.group(1))
            return max(1, min(9, n))
        except Exception:
            return 1
    if "2x2" in lower or "2 x 2" in lower or "mfrow(c(2,2))" in lower.replace(" ", ""):
        return 4
    return 1


def _rows_cols_for_n(n: int) -> Tuple[int, int]:
    if n <= 1:
        return (1, 1)
    cols = int(n ** 0.5)
    if cols * cols < n:
        cols += 1
    rows = (n + cols - 1) // cols
    return (rows, cols)


def _invoke_openai_codegen(model: str, api_key: str, messages: List[Dict[str, str]]) -> str:
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    )
    return completion.choices[0].message.content or ""


def _invoke_openai_chat(model: str, api_key: str, system: str, user: str) -> str:
    return _invoke_openai_codegen(
        model=model,
        api_key=api_key,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    ).strip()


def _run_python_in_sandbox(code: str, timeout_sec: int = 20) -> Tuple[bool, str]:
    wrapped = code.strip()
    if not wrapped:
        return (False, "Empty Python code")
    with tempfile.TemporaryDirectory(prefix="matopt_plot_") as tmpdir:
        script = Path(tmpdir) / "render_plot.py"
        script.write_text(wrapped, encoding="utf-8")
        env = {"PATH": os.getenv("PATH", ""), "PYTHONUNBUFFERED": "1"}
        try:
            proc = subprocess.run(
                ["python3", str(script)],
                cwd=tmpdir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
        except Exception as exc:
            return (False, f"Sandbox execution failed: {exc}")

        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            return (False, msg[:2000])
        return (True, (proc.stdout or "").strip())


def _generate_visual_with_python_sandbox(
    *,
    model: str,
    api_key: str,
    user_text: str,
) -> List[Dict[str, str]]:
    panel_n = _extract_panel_count(user_text)
    rows, cols = _rows_cols_for_n(panel_n)
    same_graph_preferred = _is_ode_comparison_request(user_text)
    separate_graphs_preferred = _is_min_max_saddle_bundle(user_text)
    solver_hints = _build_solver_hints(user_text)

    system = (
        "You write executable Python 3.9 code that builds graph artifacts.\n"
        "Return Python code only (no markdown fences).\n"
        "Code requirements:\n"
        "- You may use common scientific libraries if available (numpy, scipy, sympy, pandas, plotly).\n"
        "- If a library is unavailable, gracefully fall back to pure-python numeric approximation.\n"
        "- Print exactly one JSON object to stdout with schema:\n"
        '  {"assistant_markdown":"","artifacts":[{"type":"plotly|interactive_html","title":"","description":"string","code":"string"}],"tool_calls":[]}\n'
        "- For plotly artifacts, code must be a JSON string containing Plotly {data, layout, config}.\n"
        "- For interactive_html artifacts, include working JS and use Plotly.js or Chart.js only.\n"
        "- Ensure artifacts are non-empty and directly match the user's expression/problem.\n"
        "- Do not output placeholder/fallback content.\n"
    )
    if panel_n > 1:
        if same_graph_preferred:
            panel_hint = (
                f"The user asked for {panel_n} related solution curves. Render them together in the same graph "
                "(shared axes) for direct comparison."
            )
        elif separate_graphs_preferred:
            panel_hint = (
                f"The user asked for {panel_n} conceptually distinct surfaces. Render them as separate subplots "
                f"in a clear grid (mfrow-style approx {rows}x{cols}), not overlaid in one panel."
            )
        else:
            panel_hint = (
                f"The user asked for {panel_n} graphs. Decide whether to overlay traces in one figure or split into subplots "
                f"(mfrow-style approx {rows}x{cols}) based on readability and visual clarity. "
                "If curves overlap too much or represent different scales/concepts, use subplots."
            )
    else:
        panel_hint = "Use a single plot."
    user = (
        f"User request:\n{user_text}\n\n"
        f"Extra instruction:\n{panel_hint}\n\n"
        f"Solver hints:\n{solver_hints}"
    )

    repair_error = ""
    for attempt in range(3):
        retry_note = (
            ""
            if attempt == 0
            else f"\n\nPrevious execution failed with error:\n{repair_error}\nFix the code and output valid JSON."
        )
        raw = _invoke_openai_codegen(
            model=model,
            api_key=api_key,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user + retry_note},
            ],
        )
        code = _extract_python_code(raw)
        ok, stdout = _run_python_in_sandbox(code)
        if not ok:
            repair_error = stdout
            continue
        parsed = _extract_json_block(stdout)
        artifacts = _normalize_artifacts(parsed.get("artifacts", []))
        if artifacts:
            return artifacts
        repair_error = "Execution succeeded but artifacts were invalid or empty."
    return []


def _recover_corrupted_payload(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    if '"assistant_markdown"' not in text and '"artifacts"' not in text:
        return {"assistant_markdown": raw, "artifacts": [], "tool_calls": []}

    markdown = ""
    md_match = re.search(r'"assistant_markdown"\s*:\s*"(.*?)"\s*,\s*"artifacts"', text, flags=re.DOTALL)
    if md_match:
        markdown = md_match.group(1).replace("\\n", "\n").replace('\\"', '"')

    artifacts: List[Dict[str, str]] = []
    svg_match = re.search(r"(<svg[\s\S]*?</svg>)", text, flags=re.IGNORECASE)
    if svg_match:
        code = svg_match.group(1).replace('\\"', '"').replace("\\n", "\n")
        artifacts.append(
            {
                "type": "svg",
                "title": "Recovered SVG Graph",
                "description": "Recovered from malformed model JSON output.",
                "code": code,
            }
        )

    html_match = re.search(r"(<!doctype html[\s\S]*?</html>)", text, flags=re.IGNORECASE)
    if html_match:
        code = html_match.group(1).replace('\\"', '"').replace("\\n", "\n")
        artifacts.append(
            {
                "type": "interactive_html",
                "title": "Recovered Interactive Graph",
                "description": "Recovered from malformed model JSON output.",
                "code": code,
            }
        )

    tool_calls: List[Dict[str, Any]] = []
    return {"assistant_markdown": markdown, "artifacts": artifacts, "tool_calls": tool_calls}


def _unwrap_nested_payload(parsed: Dict[str, Any]) -> Dict[str, Any]:
    current = dict(parsed)
    for _ in range(3):
        markdown = current.get("assistant_markdown")
        if not isinstance(markdown, str):
            break
        candidate = markdown.strip()
        if not (candidate.startswith("{") and candidate.endswith("}")):
            break
        nested = _extract_json_block(candidate)
        if not isinstance(nested, dict):
            break
        if "assistant_markdown" not in nested and "artifacts" not in nested:
            break
        # Merge nested object; prefer explicit top-level fields when present.
        current = {
            "assistant_markdown": nested.get("assistant_markdown", ""),
            "artifacts": nested.get("artifacts", current.get("artifacts", [])),
            "tool_calls": nested.get("tool_calls", current.get("tool_calls", [])),
        }
    return current


def _extract_visuals_from_markdown(markdown: str) -> List[Dict[str, str]]:
    artifacts: List[Dict[str, str]] = []
    for lang, code in re.findall(r"```(svg|html)\n(.*?)```", markdown, flags=re.DOTALL):
        art_type = "svg" if lang == "svg" else "interactive_html"
        artifacts.append(
            {
                "type": art_type,
                "title": "Generated Visual",
                "description": "",
                "code": code.strip(),
            }
        )
    return artifacts


def _repair_code_string(code: str) -> str:
    fixed = code.strip()
    if (fixed.startswith('"') and fixed.endswith('"')) or (
        fixed.startswith("'") and fixed.endswith("'")
    ):
        fixed = fixed[1:-1]
    fixed = fixed.replace("\\n", "\n").replace('\\"', '"').replace("\\t", "\t")
    return fixed.strip()


def _looks_like_interactive_html(code: str) -> bool:
    lower = code.lower()
    has_markup = "<html" in lower or "<!doctype" in lower or "<body" in lower
    has_surface = "<canvas" in lower or "<svg" in lower
    has_logic = "<script" in lower
    return has_markup and has_surface and has_logic


def _uses_supported_interactive_lib(code: str) -> bool:
    lower = code.lower()
    chart_js_hints = (
        "new chart(" in lower
        or "chart.umd.js" in lower
        or "chart.js" in lower
    )
    plotly_hints = "plotly.newplot" in lower or "plotly" in lower
    return chart_js_hints or plotly_hints


def _contains_slider_control(code: str) -> bool:
    lower = code.lower()
    return 'type="range"' in lower or "type='range'" in lower


def _latest_user_content(messages: List[Dict[str, str]]) -> str:
    if not messages:
        return ""
    return str(messages[-1].get("content", ""))


def _extract_xy_expression(content: str) -> Optional[str]:
    if not content:
        return None
    m = re.search(r"f\s*\(\s*x\s*,\s*y\s*\)\s*=\s*([^\n.;]+)", content, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Fallback for short mentions like "x^2 + y^2" in 3D context.
    m2 = re.search(r"(x\s*(?:\^|\*\*)\s*2\s*\+\s*y\s*(?:\^|\*\*)\s*2)", content, flags=re.IGNORECASE)
    if m2:
        return m2.group(1).strip()
    return None


def _extract_xy_expressions(content: str) -> List[str]:
    if not content:
        return []
    matches = re.findall(
        r"f\s*\(\s*x\s*,\s*y\s*\)\s*=\s*([^\n.;]+)",
        content,
        flags=re.IGNORECASE,
    )
    expressions: List[str] = []
    for match in matches:
        expr = match.strip()
        if expr and expr not in expressions:
            expressions.append(expr)
    return expressions


def _is_xy_surface_request(content: str) -> bool:
    lower = content.lower()
    if "f(x,y)" in lower.replace(" ", ""):
        return True
    has_xy = "x" in lower and "y" in lower
    has_3d_hint = any(token in lower for token in ("3d", "surface", "paraboloid"))
    return has_xy and has_3d_hint


def _is_ode_comparison_request(content: str) -> bool:
    lower = content.lower()
    ode_markers = ("ode", "solve_ivp", "differential equation", "trajectory", "initial condition")
    compare_markers = ("compare", "different", "multiple", "same graph", "together")
    return any(m in lower for m in ode_markers) and any(m in lower for m in compare_markers)


def _build_solver_hints(user_text: str) -> str:
    lower = user_text.lower()
    hints: List[str] = []

    ode_markers = ("ode", "solve_ivp", "dy/d", "dx/dt", "initial condition", "ivp")
    pde_markers = ("pde", "partial differential", "heat equation", "wave equation", "laplace", "poisson")
    multi_markers = ("f(x,y)", "f(x, y)", "surface", "contour", "gradient", "hessian", "critical point")

    if any(marker in lower for marker in ode_markers):
        hints.append(
            "- ODE hint: Prefer scipy.integrate.solve_ivp when available; otherwise implement pure-Python Euler or RK4."
        )
        hints.append(
            "- ODE plotting hint: for multiple initial conditions, choose overlay or subplots based on readability."
        )

    if any(marker in lower for marker in pde_markers):
        hints.append(
            "- PDE hint: use finite-difference discretization and stable stepping parameters."
        )
        hints.append(
            "- PDE plotting hint: use heatmap/contour/surface as appropriate to dimensionality."
        )

    if any(marker in lower for marker in multi_markers):
        hints.append(
            "- Multivariable hint: create meshgrid arrays, evaluate f(x,y), and render surface/contour traces."
        )

    if not hints:
        hints.append(
            "- General hint: choose a numerically stable method and produce a graph that directly answers the question."
        )

    return "\n".join(hints)


def _is_min_max_saddle_bundle(content: str) -> bool:
    lower = content.lower()
    required = ("local minimum", "local maximum", "saddle")
    return all(token in lower for token in required)


def _wants_critical_point_highlight(content: str) -> bool:
    lower = content.lower()
    asks_location = any(token in lower for token in ("where is", "point where", "located at", "location"))
    asks_highlight = any(token in lower for token in ("highlight", "mark", "point out", "show point"))
    mentions_critical = any(token in lower for token in ("saddle", "local minimum", "local maximum", "critical point"))
    return mentions_critical and (asks_location or asks_highlight)


def _prefers_interactive_slider(content: str) -> bool:
    lower = content.lower()
    has_interactive = any(token in lower for token in ("interactive", "slider", "adjust", "parameter", "parameters"))
    return has_interactive and any(token in lower for token in ("function", "graph", "plot", "chart", "f("))


def _is_surface_plotly(code: str) -> bool:
    try:
        parsed = json.loads(code)
    except Exception:
        return False
    data = parsed.get("data")
    if not isinstance(data, list):
        return False
    for trace in data:
        if not isinstance(trace, dict):
            continue
        trace_type = str(trace.get("type", "")).lower()
        if trace_type in {"surface", "mesh3d", "scatter3d"}:
            return True
    return False


def _llm_generate_open_ended_explanation(
    *,
    model: str,
    api_key: str,
    user_request: str,
    draft_markdown: str,
    artifacts: List[Dict[str, str]],
) -> str:
    artifact_lines: List[str] = []
    for idx, artifact in enumerate(artifacts, start=1):
        artifact_lines.append(
            f"{idx}. type={artifact.get('type', '')}, caption={str(artifact.get('description', '')).strip()}"
        )
    artifacts_block = "\n".join(artifact_lines) if artifact_lines else "(no artifacts)"

    system = (
        "You are an educational math tutor.\n"
        "Rewrite/provide the core explanation aligned to the user's request and available graph artifacts.\n"
        "Requirements:\n"
        "- Start by directly answering the user's explicit question in the first sentence.\n"
        "- Provide a detailed, precise, step-by-step explanation with clear logic.\n"
        "- Keep a reasonable length: usually 2-5 short paragraphs or structured bullet steps.\n"
        "- The explanation body is primary; graph artifacts are supporting evidence only.\n"
        "- Use plain text math notation by default (e.g., f(x,y)=x^2-y^2) to avoid rendering issues.\n"
        "- Do not use LaTeX delimiters unless the user explicitly asks for LaTeX.\n"
        "- End with one natural, non-template open-ended question tailored to this topic.\n"
        "- Do not output JSON or code fences.\n"
    )
    user = (
        f"User request:\n{user_request}\n\n"
        f"Graph artifacts:\n{artifacts_block}\n\n"
        f"Draft explanation (may be empty or weak):\n{draft_markdown}\n\n"
        "Return the final explanation only."
    )
    result = _invoke_openai_chat(model=model, api_key=api_key, system=system, user=user)
    return result.strip()


def _strip_latex_delimiters(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"\\\(([\s\S]*?)\\\)", r"\1", cleaned)
    cleaned = re.sub(r"\\\[([\s\S]*?)\\\]", r"\1", cleaned)
    cleaned = cleaned.replace("$$", "")
    return cleaned


def _looks_like_structured_payload(text: str) -> bool:
    raw = text.strip()
    if not raw.startswith("{"):
        return False
    markers = ('"assistant_markdown"', '"artifacts"', '"tool_calls"')
    return any(marker in raw for marker in markers)


def _looks_like_raw_backend_material(text: str) -> bool:
    raw = text.strip()
    if not raw:
        return False
    lowered = raw.lower()
    if _looks_like_structured_payload(raw):
        return True
    markers = (
        "traceback (most recent call last):",
        "syntaxerror:",
        "backend error",
        "agentic pipeline failed",
        "import plotly.graph_objects",
        "fig.show()",
        "\"code\": \"import ",
    )
    return any(marker in lowered for marker in markers)


def _sanitize_user_markdown(markdown: str, has_artifacts: bool) -> str:
    text = markdown.strip()
    if not text:
        return ""
    if _looks_like_raw_backend_material(text):
        if has_artifacts:
            return ""
        return (
            "I ran into an internal rendering issue while preparing the response. "
            "Please try again and I can regenerate a clean explanation."
        )
    return text


def _build_visual_explanation(artifacts: List[Dict[str, str]]) -> str:
    if not artifacts:
        return ""
    lines: List[str] = [
        "Here is a step-by-step interpretation of the graph output:",
    ]
    for idx, artifact in enumerate(artifacts, start=1):
        desc = str(artifact.get("description", "")).strip()
        if desc:
            lines.append(f"{idx}. {desc}")
        else:
            lines.append(f"{idx}. Graph {idx} is rendered for the requested topic.")
    return "\n".join(lines)


def _normalize_artifacts(raw_artifacts: Any) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    if not isinstance(raw_artifacts, list):
        return normalized

    for idx, item in enumerate(raw_artifacts):
        if not isinstance(item, dict):
            continue
        art_type = str(item.get("type", "")).strip().lower()
        if art_type not in {"interactive_html", "plotly"}:
            continue
        code = _repair_code_string(str(item.get("code", "")))
        if not code:
            continue

        title = str(item.get("title", "")).strip() or f"Visual {idx + 1}"
        description = str(item.get("description", "")).strip()
        if art_type == "interactive_html":
            code = sanitize_interactive_html(code)
            if not _looks_like_interactive_html(code):
                continue
            if not _uses_supported_interactive_lib(code):
                continue
        else:
            try:
                parsed = json.loads(code)
                if not isinstance(parsed, dict) or "data" not in parsed:
                    continue
            except Exception:
                continue

        normalized.append(
            {
                "type": art_type,
                "title": title,
                "description": description,
                "code": code,
            }
        )
    return normalized


def _wants_visual(messages: List[Dict[str, str]]) -> bool:
    if not messages:
        return False
    content = messages[-1].get("content", "").lower()
    explicit_hints = (
        "graph",
        "plot",
        "visual",
        "visualize",
        "chart",
        "svg",
        "interactive",
        "html",
        "diagram",
    )
    if any(token in content for token in explicit_hints):
        return True

    # Implicit visual intent: user asks for comparison/trend/distribution style analysis.
    implicit_pairs = (
        ("compare", "data"),
        ("trend", "data"),
        ("distribution", "data"),
        ("breakdown", "data"),
        ("relationship", "variables"),
    )
    return any(a in content and b in content for a, b in implicit_pairs)


def _is_text_only_intent(messages: List[Dict[str, str]]) -> bool:
    if not messages:
        return False
    content = messages[-1].get("content", "").lower()
    text_first_hints = (
        "summarize",
        "explain",
        "review",
        "proofread",
        "rewrite",
        "improve wording",
        "translate",
        "what is",
        "why is",
    )
    # If user explicitly asks for visual output, never force text-only.
    visual_hints = ("graph", "plot", "chart", "visualize", "diagram", "svg", "interactive")
    if any(v in content for v in visual_hints):
        return False
    return any(t in content for t in text_first_hints)


def _load_skills(skill_slugs: List[str] | None) -> List[Dict[str, Any]]:
    if not skill_slugs:
        return []
    loaded: List[Dict[str, Any]] = []
    for slug in skill_slugs:
        try:
            skill = read_skill(slug)
            loaded.append(skill)
        except FileNotFoundError:
            continue
    return loaded


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_]{3,}", text.lower())


def _build_langchain_skill_documents(skills: List[Dict[str, Any]]) -> List[Any]:
    docs: List[Any] = []
    if not skills or Document is None:
        return docs

    for skill in skills:
        slug = str(skill.get("slug", "")).strip() or "unknown-skill"
        title = str(skill.get("title", slug)).strip()
        skill_md = str(skill.get("content", "")).strip()
        if skill_md:
            docs.append(
                Document(
                    page_content=skill_md[:6000],
                    metadata={"skill_slug": slug, "source": "SKILL.md", "title": title},
                )
            )

        for key, source_label in (
            ("text_references", "reference"),
            ("python_templates", "python_template"),
        ):
            entries = skill.get(key, [])
            if not isinstance(entries, list):
                continue
            for item in entries[:8]:
                if not isinstance(item, dict):
                    continue
                rel_path = str(item.get("path", "")).strip()
                content = str(item.get("content", "")).strip()
                if not content:
                    continue
                docs.append(
                    Document(
                        page_content=content[:4000],
                        metadata={
                            "skill_slug": slug,
                            "source": source_label,
                            "path": rel_path,
                            "title": title,
                        },
                    )
                )
    return docs


def _select_skill_documents_for_query(query: str, docs: List[Any], limit: int = 8) -> List[Any]:
    if not docs:
        return []
    tokens = set(_tokenize(query))
    if not tokens:
        return docs[:limit]

    scored: List[Tuple[int, Any]] = []
    for doc in docs:
        content = str(getattr(doc, "page_content", "")).lower()
        meta = getattr(doc, "metadata", {}) or {}
        source = str(meta.get("source", "")).lower()
        skill_slug = str(meta.get("skill_slug", "")).lower()
        overlap = 0
        for token in tokens:
            if token in content:
                overlap += 1
            if token in skill_slug:
                overlap += 2
        if source == "python_template":
            overlap += 1
        scored.append((overlap, doc))

    scored.sort(key=lambda row: row[0], reverse=True)
    return [doc for score, doc in scored if score > 0][:limit] or docs[:limit]


def _skill_context_node(state: AgentRunState) -> AgentRunState:
    skills = state.get("skills", [])
    messages = state.get("messages", [])
    query = messages[-1].get("content", "") if messages else ""

    docs = _build_langchain_skill_documents(skills)
    selected_docs = _select_skill_documents_for_query(query, docs, limit=8)

    chunks: List[str] = []
    for doc in selected_docs:
        meta = getattr(doc, "metadata", {}) or {}
        slug = str(meta.get("skill_slug", "unknown"))
        source = str(meta.get("source", "doc"))
        path = str(meta.get("path", "")).strip()
        label = f"[{slug}] {source}" + (f" ({path})" if path else "")
        body = str(getattr(doc, "page_content", "")).strip()
        if body:
            chunks.append(f"{label}\n{body[:1800]}")

    return {"linked_skill_context": "\n\n".join(chunks)}


def _select_python_templates(skill_slug: str, query: str, max_files: int = 3) -> List[Dict[str, str]]:
    skill_root = Path(__file__).resolve().parent / "skills" / skill_slug
    if not skill_root.exists():
        return []

    query_tokens = set(_tokenize(query))
    scored: List[tuple[int, Path]] = []
    for py_path in skill_root.rglob("*.py"):
        if py_path.name.startswith("."):
            continue
        try:
            content = py_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        score = 0
        lower_path = str(py_path.relative_to(skill_root)).lower()
        for token in query_tokens:
            if token in lower_path:
                score += 4
            if token in content.lower():
                score += 1
        if "example" in lower_path or "script" in lower_path:
            score += 1
        scored.append((score, py_path))

    scored.sort(key=lambda row: (-row[0], str(row[1])))
    selected = [path for _, path in scored[:max_files]]
    templates: List[Dict[str, str]] = []
    for path in selected:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        templates.append(
            {
                "path": str(path.relative_to(skill_root)),
                "content": raw[:2400],
            }
        )
    return templates


def _score_file_for_query(rel_path: str, content: str, query_tokens: set[str]) -> int:
    score = 0
    low_rel = rel_path.lower()
    low_content = content.lower()
    for token in query_tokens:
        if token in low_rel:
            score += 4
        if token in low_content:
            score += 1
    if any(k in low_rel for k in ("example", "reference", "script", "template")):
        score += 1
    return score


def _select_text_references(
    skill_slug: str,
    query: str,
    max_files: int = 3,
) -> List[Dict[str, str]]:
    skill_root = Path(__file__).resolve().parent / "skills" / skill_slug
    if not skill_root.exists():
        return []

    query_tokens = set(_tokenize(query))
    candidates: List[Tuple[int, Path, str]] = []
    for ext in ("*.md", "*.yaml", "*.yml", "*.txt"):
        for path in skill_root.rglob(ext):
            name = path.name.lower()
            if name.startswith("license"):
                continue
            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            rel = str(path.relative_to(skill_root))
            score = _score_file_for_query(rel, raw[:6000], query_tokens)
            candidates.append((score, path, raw))

    candidates.sort(key=lambda row: (-row[0], str(row[1])))
    selected: List[Dict[str, str]] = []
    for _, path, raw in candidates[:max_files]:
        selected.append(
            {
                "path": str(path.relative_to(skill_root)),
                "content": raw[:2200],
            }
        )
    return selected


def _load_skill_packages(skill_slugs: List[str] | None, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    skills = _load_skills(skill_slugs)
    if not skills:
        return []
    query = messages[-1].get("content", "") if messages else ""
    packages: List[Dict[str, Any]] = []
    for skill in skills:
        slug = str(skill.get("slug", "")).strip()
        packages.append(
            {
                **skill,
                "python_templates": _select_python_templates(slug, query=query, max_files=3),
                "text_references": _select_text_references(slug, query=query, max_files=3),
            }
        )
    return packages


def _invoke_chat_openai(model: str, api_key: str, messages: List[Dict[str, str]]) -> str:
    llm = ChatOpenAI(model=model, temperature=0.2, api_key=api_key)
    normalized = [
        (str(m.get("role", "user")), str(m.get("content", "")))
        for m in messages
        if m.get("content")
    ]
    response = llm.invoke(normalized)
    content = getattr(response, "content", "")
    if isinstance(content, list):
        collected: List[str] = []
        for part in content:
            if isinstance(part, str):
                collected.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    collected.append(text)
        return "".join(collected).strip() or "".join(str(part) for part in content)
    return str(content)


def _plan_node(state: AgentRunState) -> AgentRunState:
    messages = state.get("messages", [])
    system = {
        "role": "system",
        "content": "You are a planning agent. Return a concise plan in bullet points.",
    }
    content = _invoke_chat_openai(
        model=state["model"],
        api_key=state["api_key"],
        messages=[system, *messages[-6:]],
    )
    return {"plan": content}


def _generate_node(state: AgentRunState) -> AgentRunState:
    messages = state.get("messages", [])
    skills = state.get("skills", [])
    skill_blocks: List[str] = []
    for skill in skills:
        slug = skill.get("slug", "unknown")
        md = str(skill.get("content", ""))[:2400]
        python_templates = skill.get("python_templates", [])
        text_references = skill.get("text_references", [])
        py_sections: List[str] = []
        if isinstance(python_templates, list):
            for tpl in python_templates[:3]:
                if not isinstance(tpl, dict):
                    continue
                rel_path = str(tpl.get("path", "template.py"))
                code = str(tpl.get("content", ""))
                if not code.strip():
                    continue
                py_sections.append(f"template: {rel_path}\n```python\n{code}\n```")
        block = f"[{slug}]\nSKILL.md excerpt:\n{md}"
        ref_sections: List[str] = []
        if isinstance(text_references, list):
            for ref in text_references[:3]:
                if not isinstance(ref, dict):
                    continue
                rel_path = str(ref.get("path", "reference.md"))
                content = str(ref.get("content", ""))
                if content.strip():
                    ref_sections.append(f"reference: {rel_path}\n{content}")

        if ref_sections:
            block += "\nReferences:\n" + "\n\n".join(ref_sections)
        if py_sections:
            block += "\nPython templates:\n" + "\n\n".join(py_sections)
        skill_blocks.append(block)
    skill_context = "\n\n".join(skill_blocks)
    linked_skill_context = str(state.get("linked_skill_context", "")).strip()
    merged_skill_context = (
        f"{linked_skill_context}\n\n{skill_context}".strip()
        if linked_skill_context
        else skill_context
    )
    system = {
        "role": "system",
        "content": (
            "You are a visualization-focused coding assistant. "
            "Prefer concise explanations with accurate code.\n"
            f"{EDUCATION_STYLE_INSTRUCTION}\n"
            "When skill Python templates are provided, adapt those templates to the user's exact requirement.\n"
            "Do not output starter placeholders when the user requested a specific function/visual.\n"
            "For visual requests, default to Plotly artifacts tailored to the exact prompt.\n"
            "Do not use static fallback shapes or unrelated sample charts.\n"
            "Never emit SVG artifacts.\n"
            "For interactive_html artifacts, use only Chart.js or Plotly.js and include working JS.\n"
            "When plotting a tunable function in interactive_html, include at least one range slider to control parameters.\n"
            "For 3D requests involving f(x,y), use a true Plotly surface/3D trace instead of a 2D line chart.\n"
            "Do not include graph titles in artifacts; keep title as an empty string.\n"
            "Put brief graph explanation only in artifact.description (caption style), not in assistant_markdown.\n"
            f"{VISUAL_JSON_INSTRUCTION}\n\n"
            f"- planning notes:\n{state.get('plan', '')[:1200]}\n"
            f"- skill context:\n{merged_skill_context[:5000]}"
        ),
    }

    raw_output = _invoke_chat_openai(
        model=state["model"],
        api_key=state["api_key"],
        messages=[system, *messages],
    )
    return {"raw_output": raw_output}


def _validate_node(state: AgentRunState) -> AgentRunState:
    raw_output = state.get("raw_output", "")
    parsed = _unwrap_nested_payload(_extract_json_block(raw_output))
    if (
        not parsed.get("artifacts")
        and isinstance(parsed.get("assistant_markdown"), str)
        and '"assistant_markdown"' in str(parsed.get("assistant_markdown"))
    ):
        parsed = _unwrap_nested_payload(_recover_corrupted_payload(str(parsed.get("assistant_markdown"))))
    if not parsed.get("artifacts") and '"assistant_markdown"' in str(raw_output):
        parsed = _unwrap_nested_payload(_recover_corrupted_payload(str(raw_output)))
    markdown = str(parsed.get("assistant_markdown", "")).strip()
    tool_calls = parsed.get("tool_calls", [])
    artifacts = _normalize_artifacts(parsed.get("artifacts", []))
    if not artifacts and markdown:
        artifacts = _normalize_artifacts(_extract_visuals_from_markdown(markdown))

    wants_visual = _wants_visual(state.get("messages", []))
    text_only = _is_text_only_intent(state.get("messages", []))
    latest_user = _latest_user_content(state.get("messages", []))
    if wants_visual and not text_only and not artifacts:
        # Generate plotting code dynamically and execute in sandbox.
        try:
            sandbox_artifacts = _generate_visual_with_python_sandbox(
                model=state["model"],
                api_key=state["api_key"],
                user_text=latest_user,
            )
            if sandbox_artifacts:
                artifacts = sandbox_artifacts
                tool_calls = [
                    *tool_calls,
                    {"name": "run_python_plot_sandbox", "arguments": {"artifacts": len(sandbox_artifacts)}},
                ]
                markdown = ""
        except Exception:
            artifacts = []

    if wants_visual and not text_only and not artifacts:
        markdown = (
            "I could not generate a valid plot from the requested expression this time. "
            "Please restate the exact equation/system (and any initial/boundary conditions), and I will regenerate."
        )

    # Hard guardrail: if user intent is text-first and not explicitly visual, suppress artifacts.
    if artifacts and (text_only or not wants_visual):
        artifacts = []
    elif artifacts and wants_visual and markdown:
        compact_markdown = re.sub(r"\s+", " ", markdown).strip()
        looks_like_caption = (
            len(compact_markdown) <= 220
            or compact_markdown.lower().startswith("graph illustrating")
            or compact_markdown.lower().startswith("chart illustrating")
        )
        if looks_like_caption:
            if not str(artifacts[0].get("description", "")).strip():
                artifacts[0]["description"] = compact_markdown
            markdown = ""

    if markdown.strip().startswith("{") and '"assistant_markdown"' in markdown:
        markdown = "I generated the requested visual output."

    markdown = _sanitize_user_markdown(markdown, has_artifacts=bool(artifacts))
    if not markdown and artifacts:
        markdown = _build_visual_explanation(artifacts)
    if artifacts:
        try:
            llm_markdown = _llm_generate_open_ended_explanation(
                model=state["model"],
                api_key=state["api_key"],
                user_request=latest_user,
                draft_markdown=markdown,
                artifacts=artifacts,
            )
            if llm_markdown:
                markdown = _strip_latex_delimiters(llm_markdown)
        except Exception:
            pass
    markdown = _sanitize_user_markdown(markdown, has_artifacts=bool(artifacts))
    if not markdown and artifacts:
        markdown = _build_visual_explanation(artifacts)

    # Prevent leaking raw model JSON/Python payload text into chat when artifacts exist.
    final_markdown = markdown
    if artifacts and not final_markdown:
        final_markdown = ""
    elif not artifacts and not final_markdown:
        raw_text = str(state.get("raw_output", "")).strip()
        looks_structured_blob = (
            raw_text.startswith("{")
            and ('"assistant_markdown"' in raw_text or '"artifacts"' in raw_text)
        )
        final_markdown = (
            "I couldn't render a valid graph from the generated code. "
            "Please refine the request (for example specify the exact functions and preferred layout), and I can retry."
            if looks_structured_blob
            else raw_text
        )

    return {
        "result": {
            "assistant_markdown": final_markdown,
            "artifacts": artifacts,
            "tool_calls": tool_calls if isinstance(tool_calls, list) else [],
            "agent_mode": "langgraph" if LANGGRAPH_AVAILABLE else "openai-fallback",
        }
    }


def _compile_graph():
    graph = StateGraph(AgentRunState)
    graph.add_node("plan", _plan_node)
    graph.add_node("skill_context", _skill_context_node)
    graph.add_node("generate", _generate_node)
    graph.add_node("validate", _validate_node)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "skill_context")
    graph.add_edge("skill_context", "generate")
    graph.add_edge("generate", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


def run_agentic_chat(
    openai_client: OpenAI,
    model: str,
    api_key: str,
    messages: List[Dict[str, str]],
    skill_slugs: List[str] | None = None,
) -> Dict[str, Any]:
    skills = _load_skill_packages(skill_slugs, messages=messages)

    if LANGGRAPH_AVAILABLE:
        global _GRAPH
        if _GRAPH is None:
            _GRAPH = _compile_graph()
        result_state = _GRAPH.invoke(
            {
                "messages": messages,
                "model": model,
                "api_key": api_key,
                "skills": skills,
            }
        )
        result = result_state.get("result", {})
        return result if isinstance(result, dict) else {}

    # Graceful fallback when langchain/langgraph dependencies are unavailable.
    system_prompt = (
        "You are a visualization-focused coding assistant.\n"
        f"{EDUCATION_STYLE_INSTRUCTION}\n"
        f"{VISUAL_JSON_INSTRUCTION}"
    )
    completion = openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, *messages],
        temperature=0.2,
    )
    raw = completion.choices[0].message.content or ""
    parsed = _unwrap_nested_payload(_extract_json_block(raw))
    artifacts = _normalize_artifacts(parsed.get("artifacts", []))
    fallback_markdown = str(parsed.get("assistant_markdown", "")).strip()

    # Never leak raw structured JSON payloads into user-visible markdown.
    if not fallback_markdown and artifacts:
        fallback_markdown = ""
    elif not fallback_markdown:
        fallback_markdown = raw.strip()
        if _looks_like_structured_payload(fallback_markdown):
            fallback_markdown = (
                "I generated visual output and validated the artifacts. "
                "If you want, I can refine layout or styling for better readability."
            )

    fallback_markdown = _sanitize_user_markdown(fallback_markdown, has_artifacts=bool(artifacts))
    if not fallback_markdown and artifacts:
        fallback_markdown = _build_visual_explanation(artifacts)
    if artifacts:
        latest_user = _latest_user_content(messages)
        try:
            llm_markdown = _llm_generate_open_ended_explanation(
                model=model,
                api_key=api_key,
                user_request=latest_user,
                draft_markdown=fallback_markdown,
                artifacts=artifacts,
            )
            if llm_markdown:
                fallback_markdown = _strip_latex_delimiters(llm_markdown)
        except Exception:
            pass
        fallback_markdown = _sanitize_user_markdown(fallback_markdown, has_artifacts=True)
        if not fallback_markdown:
            fallback_markdown = _build_visual_explanation(artifacts)
    return {
        "assistant_markdown": fallback_markdown,
        "artifacts": artifacts,
        "tool_calls": parsed.get("tool_calls", []) if isinstance(parsed.get("tool_calls"), list) else [],
        "agent_mode": "openai-fallback",
    }

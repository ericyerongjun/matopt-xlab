from __future__ import annotations

import ast
import json
import math
import re
from html import escape
from typing import Any, Callable, Dict, List
from xml.etree import ElementTree as ET


def create_svg_scaffold(title: str, x_label: str = "X", y_label: str = "Y") -> str:
    safe_title = escape(title or "Graph")
    safe_x = escape(x_label)
    safe_y = escape(y_label)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 480" role="img" aria-label="{safe_title}">
  <title>{safe_title}</title>
  <rect width="800" height="480" fill="#f8fafc" />
  <line x1="90" y1="70" x2="90" y2="400" stroke="#334155" stroke-width="2" />
  <line x1="90" y1="400" x2="740" y2="400" stroke="#334155" stroke-width="2" />
  <text x="420" y="445" text-anchor="middle" fill="#0f172a" font-size="18">{safe_x}</text>
  <text x="32" y="235" text-anchor="middle" fill="#0f172a" font-size="18" transform="rotate(-90 32 235)">{safe_y}</text>
  <polyline fill="none" stroke="#2563eb" stroke-width="4"
    points="120,370 210,320 300,250 390,230 480,180 570,140 660,95" />
  <circle cx="120" cy="370" r="5" fill="#2563eb" />
  <circle cx="210" cy="320" r="5" fill="#2563eb" />
  <circle cx="300" cy="250" r="5" fill="#2563eb" />
  <circle cx="390" cy="230" r="5" fill="#2563eb" />
  <circle cx="480" cy="180" r="5" fill="#2563eb" />
  <circle cx="570" cy="140" r="5" fill="#2563eb" />
  <circle cx="660" cy="95" r="5" fill="#2563eb" />
</svg>"""


def create_interactive_html_scaffold(title: str) -> str:
    safe_title = escape(title or "Interactive Graph")
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{safe_title}</title>
    <style>
      :root {{
        color-scheme: light;
      }}
      body {{
        margin: 0;
        font-family: "IBM Plex Sans", system-ui, sans-serif;
        background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        color: #0f172a;
      }}
      .wrap {{
        padding: 24px;
      }}
      .panel {{
        background: #ffffffcc;
        backdrop-filter: blur(4px);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 16px;
      }}
      #chart {{
        width: 100%;
        height: 360px;
      }}
      label {{
        display: block;
        margin-bottom: 10px;
      }}
      input[type="range"] {{
        width: 320px;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="panel">
        <h2>{safe_title}</h2>
        <label>Frequency: <input id="freq" type="range" min="1" max="10" value="3" /></label>
        <svg id="chart" viewBox="0 0 700 360" aria-label="{safe_title}"></svg>
      </div>
    </div>
    <script>
      const svg = document.getElementById("chart");
      const slider = document.getElementById("freq");
      function draw(freq) {{
        const points = [];
        for (let i = 0; i <= 120; i += 1) {{
          const x = 40 + i * 5.2;
          const y = 180 - Math.sin((i / 120) * Math.PI * 2 * freq) * 110;
          points.push(`${{x.toFixed(2)}},${{y.toFixed(2)}}`);
        }}
        svg.innerHTML = `
          <rect x="0" y="0" width="700" height="360" fill="#f8fafc"></rect>
          <line x1="40" y1="180" x2="680" y2="180" stroke="#64748b" stroke-width="1.5"></line>
          <line x1="40" y1="20" x2="40" y2="340" stroke="#64748b" stroke-width="1.5"></line>
          <polyline points="${{points.join(" ")}}" fill="none" stroke="#2563eb" stroke-width="3"></polyline>
        `;
      }}
      slider.addEventListener("input", () => draw(Number(slider.value)));
      draw(Number(slider.value));
    </script>
  </body>
</html>"""


def create_paraboloid_svg(title: str = "f(x, y) = x^2 + y^2") -> str:
    safe_title = escape(title)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 520" role="img" aria-label="{safe_title}">
  <title>{safe_title}</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f8fbff" />
      <stop offset="100%" stop-color="#eef4ff" />
    </linearGradient>
    <radialGradient id="surface" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#8ec5ff" stop-opacity="0.8" />
      <stop offset="100%" stop-color="#2563eb" stop-opacity="0.18" />
    </radialGradient>
  </defs>
  <rect width="860" height="520" fill="url(#bg)" />
  <g transform="translate(430,300)">
    <ellipse cx="0" cy="0" rx="255" ry="90" fill="url(#surface)" />
    <ellipse cx="0" cy="0" rx="220" ry="78" fill="none" stroke="#5d84e8" stroke-opacity="0.65" />
    <ellipse cx="0" cy="0" rx="180" ry="64" fill="none" stroke="#5d84e8" stroke-opacity="0.5" />
    <ellipse cx="0" cy="0" rx="140" ry="50" fill="none" stroke="#5d84e8" stroke-opacity="0.42" />
    <ellipse cx="0" cy="0" rx="100" ry="35" fill="none" stroke="#5d84e8" stroke-opacity="0.35" />
    <ellipse cx="0" cy="0" rx="60" ry="22" fill="none" stroke="#5d84e8" stroke-opacity="0.28" />
    <line x1="-285" y1="0" x2="285" y2="0" stroke="#334155" stroke-width="2" />
    <line x1="0" y1="130" x2="0" y2="-190" stroke="#334155" stroke-width="2" />
    <line x1="-190" y1="90" x2="190" y2="-90" stroke="#64748b" stroke-width="2" stroke-dasharray="4 5" />
    <circle cx="0" cy="0" r="5" fill="#1d4ed8" />
    <text x="10" y="-10" fill="#1e293b" font-size="16">(0,0,0)</text>
    <text x="295" y="4" fill="#0f172a" font-size="18">x</text>
    <text x="7" y="-198" fill="#0f172a" font-size="18">z</text>
    <text x="-210" y="107" fill="#334155" font-size="18">y</text>
  </g>
  <text x="28" y="38" fill="#0f172a" font-size="24" font-family="ui-sans-serif, system-ui, sans-serif">{safe_title}</text>
</svg>"""


def create_paraboloid_interactive_html(title: str = "Interactive f(x, y) = x^2 + y^2") -> str:
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{safe_title}</title>
    <style>
      body {{
        margin: 0;
        font-family: "IBM Plex Sans", system-ui, sans-serif;
        background: #0f172a;
        color: #e2e8f0;
      }}
      .wrap {{
        padding: 14px;
      }}
      .panel {{
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 12px;
      }}
      .controls {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        margin-bottom: 10px;
      }}
      label {{
        font-size: 13px;
        color: #94a3b8;
      }}
      input[type="range"] {{
        width: 160px;
      }}
      canvas {{
        width: 100%;
        height: 380px;
        background: radial-gradient(circle at 50% 35%, #1f2937 0%, #0b1220 70%);
        border-radius: 10px;
        border: 1px solid #243244;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="panel">
        <div class="controls">
          <strong>{safe_title}</strong>
          <label>Scale <input id="scale" type="range" min="8" max="30" value="16" /></label>
          <label>Pitch <input id="pitch" type="range" min="20" max="80" value="52" /></label>
          <label>Yaw <input id="yaw" type="range" min="-180" max="180" value="-35" /></label>
        </div>
        <canvas id="cv" width="980" height="500" aria-label="{safe_title}"></canvas>
      </div>
    </div>
    <script>
      const cv = document.getElementById("cv");
      const ctx = cv.getContext("2d");
      const scaleEl = document.getElementById("scale");
      const pitchEl = document.getElementById("pitch");
      const yawEl = document.getElementById("yaw");

      function rot(x, y, z, pitch, yaw) {{
        const cy = Math.cos(yaw), sy = Math.sin(yaw);
        const cp = Math.cos(pitch), sp = Math.sin(pitch);
        const x1 = x * cy + z * sy;
        const z1 = -x * sy + z * cy;
        const y2 = y * cp - z1 * sp;
        const z2 = y * sp + z1 * cp;
        return [x1, y2, z2];
      }}

      function draw() {{
        const w = cv.width, h = cv.height;
        ctx.clearRect(0, 0, w, h);
        const scale = Number(scaleEl.value);
        const pitch = Number(pitchEl.value) * Math.PI / 180;
        const yaw = Number(yawEl.value) * Math.PI / 180;
        const xMin = -3, xMax = 3, yMin = -3, yMax = 3, step = 0.18;
        const rows = [];
        for (let yy = yMin; yy <= yMax + 1e-9; yy += step) {{
          const row = [];
          for (let xx = xMin; xx <= xMax + 1e-9; xx += step) {{
            const zz = xx * xx + yy * yy;
            row.push([xx, yy, zz]);
          }}
          rows.push(row);
        }}

        const projected = [];
        for (const row of rows) {{
          const pRow = [];
          for (const [x, y, z] of row) {{
            const [rx, ry, rz] = rot(x, y, z, pitch, yaw);
            const perspective = 1 / (1 + rz * 0.06);
            const sx = w * 0.5 + rx * scale * 18 * perspective;
            const sy = h * 0.78 - ry * scale * 10 * perspective - z * scale * 0.9;
            pRow.push([sx, sy, z]);
          }}
          projected.push(pRow);
        }}

        for (let i = 0; i < projected.length - 1; i++) {{
          for (let j = 0; j < projected[i].length - 1; j++) {{
            const p1 = projected[i][j], p2 = projected[i][j + 1];
            const p3 = projected[i + 1][j + 1], p4 = projected[i + 1][j];
            const zAvg = (p1[2] + p2[2] + p3[2] + p4[2]) * 0.25;
            const t = Math.min(1, zAvg / 18);
            const b = Math.round(255 - t * 120);
            ctx.fillStyle = `rgba(${{70 + Math.round(t * 40)}}, ${{130 + Math.round(t * 30)}}, ${{b}}, 0.65)`;
            ctx.beginPath();
            ctx.moveTo(p1[0], p1[1]);
            ctx.lineTo(p2[0], p2[1]);
            ctx.lineTo(p3[0], p3[1]);
            ctx.lineTo(p4[0], p4[1]);
            ctx.closePath();
            ctx.fill();
          }}
        }}

        ctx.strokeStyle = "#94a3b8";
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(w * 0.1, h * 0.78);
        ctx.lineTo(w * 0.9, h * 0.78);
        ctx.moveTo(w * 0.5, h * 0.92);
        ctx.lineTo(w * 0.5, h * 0.18);
        ctx.stroke();
      }}

      [scaleEl, pitchEl, yawEl].forEach((el) => el.addEventListener("input", draw));
      draw();
    </script>
  </body>
</html>"""


def create_hyperbolic_paraboloid_ab_slider_html(
    title: str = "Interactive f(x, y) = a*x^2 - b*y^2",
    *,
    a_min: float = -3.0,
    a_max: float = 3.0,
    a_step: float = 0.1,
    a_default: float = 1.0,
    b_min: float = -3.0,
    b_max: float = 3.0,
    b_step: float = 0.1,
    b_default: float = 1.0,
    scale_min: float = 8.0,
    scale_max: float = 28.0,
    scale_step: float = 1.0,
    scale_default: float = 16.0,
) -> str:
    safe_title = escape(title)
    a_min_s = f"{a_min:g}"
    a_max_s = f"{a_max:g}"
    a_step_s = f"{a_step:g}"
    a_default_s = f"{a_default:g}"
    b_min_s = f"{b_min:g}"
    b_max_s = f"{b_max:g}"
    b_step_s = f"{b_step:g}"
    b_default_s = f"{b_default:g}"
    scale_min_s = f"{scale_min:g}"
    scale_max_s = f"{scale_max:g}"
    scale_step_s = f"{scale_step:g}"
    scale_default_s = f"{scale_default:g}"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{safe_title}</title>
    <style>
      body {{
        margin: 0;
        font-family: "IBM Plex Sans", system-ui, sans-serif;
        background: #0b1220;
        color: #e2e8f0;
      }}
      .wrap {{
        padding: 14px;
      }}
      .panel {{
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 12px;
      }}
      .controls {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 8px 14px;
        align-items: center;
        margin-bottom: 10px;
      }}
      .formula {{
        font-size: 12px;
        color: #cbd5e1;
      }}
      label {{
        font-size: 13px;
        color: #94a3b8;
      }}
      input[type="range"] {{
        width: 100%;
      }}
      canvas {{
        width: 100%;
        height: 390px;
        background: radial-gradient(circle at 50% 35%, #1f2937 0%, #0b1220 70%);
        border-radius: 10px;
        border: 1px solid #243244;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="panel">
        <div class="controls">
          <strong>{safe_title}</strong>
          <label>
            a: <span id="aVal">{a_default_s}</span>
            <input id="a" type="range" min="{a_min_s}" max="{a_max_s}" step="{a_step_s}" value="{a_default_s}" />
          </label>
          <label>
            b: <span id="bVal">{b_default_s}</span>
            <input id="b" type="range" min="{b_min_s}" max="{b_max_s}" step="{b_step_s}" value="{b_default_s}" />
          </label>
          <label>
            Scale: <span id="scaleVal">{scale_default_s}</span>
            <input id="scale" type="range" min="{scale_min_s}" max="{scale_max_s}" step="{scale_step_s}" value="{scale_default_s}" />
          </label>
        </div>
        <div class="formula" id="formula">f(x, y) = {a_default_s}*x^2 - {b_default_s}*y^2</div>
        <canvas id="cv" width="980" height="500" aria-label="{safe_title}"></canvas>
      </div>
    </div>
    <script>
      const cv = document.getElementById("cv");
      const ctx = cv.getContext("2d");
      const aEl = document.getElementById("a");
      const bEl = document.getElementById("b");
      const scaleEl = document.getElementById("scale");
      const aVal = document.getElementById("aVal");
      const bVal = document.getElementById("bVal");
      const scaleVal = document.getElementById("scaleVal");
      const formulaEl = document.getElementById("formula");

      function rot(x, y, z, pitch, yaw) {{
        const cy = Math.cos(yaw), sy = Math.sin(yaw);
        const cp = Math.cos(pitch), sp = Math.sin(pitch);
        const x1 = x * cy + z * sy;
        const z1 = -x * sy + z * cy;
        const y2 = y * cp - z1 * sp;
        const z2 = y * sp + z1 * cp;
        return [x1, y2, z2];
      }}

      function draw() {{
        const w = cv.width;
        const h = cv.height;
        ctx.clearRect(0, 0, w, h);

        const a = Number(aEl.value);
        const b = Number(bEl.value);
        const scale = Number(scaleEl.value);
        aVal.textContent = a.toFixed(2);
        bVal.textContent = b.toFixed(2);
        scaleVal.textContent = String(scale);
        formulaEl.textContent = `f(x, y) = ${{a.toFixed(2)}}*x^2 - ${{b.toFixed(2)}}*y^2`;

        const pitch = 54 * Math.PI / 180;
        const yaw = -38 * Math.PI / 180;
        const xMin = -3, xMax = 3, yMin = -3, yMax = 3, step = 0.2;

        const rows = [];
        for (let yy = yMin; yy <= yMax + 1e-9; yy += step) {{
          const row = [];
          for (let xx = xMin; xx <= xMax + 1e-9; xx += step) {{
            const zz = a * xx * xx - b * yy * yy;
            row.push([xx, yy, zz]);
          }}
          rows.push(row);
        }}

        const projected = [];
        for (const row of rows) {{
          const pRow = [];
          for (const [x, y, z] of row) {{
            const [rx, ry, rz] = rot(x, y, z, pitch, yaw);
            const perspective = 1 / (1 + rz * 0.05);
            const sx = w * 0.5 + rx * scale * 18 * perspective;
            const sy = h * 0.76 - ry * scale * 9 * perspective - z * scale * 0.8;
            pRow.push([sx, sy, z]);
          }}
          projected.push(pRow);
        }}

        for (let i = 0; i < projected.length - 1; i++) {{
          for (let j = 0; j < projected[i].length - 1; j++) {{
            const p1 = projected[i][j], p2 = projected[i][j + 1];
            const p3 = projected[i + 1][j + 1], p4 = projected[i + 1][j];
            const zAvg = (p1[2] + p2[2] + p3[2] + p4[2]) * 0.25;
            const t = Math.max(0, Math.min(1, (zAvg + 12) / 24));
            const r = Math.round(80 + t * 90);
            const g = Math.round(120 + t * 85);
            const bl = Math.round(220 - t * 140);
            ctx.fillStyle = `rgba(${{r}}, ${{g}}, ${{bl}}, 0.66)`;
            ctx.beginPath();
            ctx.moveTo(p1[0], p1[1]);
            ctx.lineTo(p2[0], p2[1]);
            ctx.lineTo(p3[0], p3[1]);
            ctx.lineTo(p4[0], p4[1]);
            ctx.closePath();
            ctx.fill();
          }}
        }}

        ctx.strokeStyle = "#94a3b8";
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(w * 0.1, h * 0.76);
        ctx.lineTo(w * 0.9, h * 0.76);
        ctx.moveTo(w * 0.5, h * 0.9);
        ctx.lineTo(w * 0.5, h * 0.18);
        ctx.stroke();
      }}

      [aEl, bEl, scaleEl].forEach((el) => el.addEventListener("input", draw));
      draw();
    </script>
  </body>
</html>"""


def create_ab_tunable_surface_plotly_json(
    *,
    operator: str = "minus",
    a_min: float = -2.5,
    a_max: float = 2.5,
    a_step: float = 0.1,
    a_default: float = 1.0,
    b_min: float = -2.5,
    b_max: float = 2.5,
    b_step: float = 0.1,
    b_default: float = 1.0,
) -> str:
    xs = [round(-3 + i * 0.2, 3) for i in range(31)]
    ys = [round(-3 + i * 0.2, 3) for i in range(31)]
    op_sign = 1.0 if operator == "plus" else -1.0
    z = [
        [round(a_default * x * x + op_sign * b_default * y * y, 6) for x in xs]
        for y in ys
    ]
    payload = {
        "data": [
            {
                "type": "surface",
                "x": xs,
                "y": ys,
                "z": z,
                "colorscale": "Viridis",
                "showscale": True,
                "contours": {"z": {"show": True, "usecolormap": True, "highlightwidth": 1}},
                "hovertemplate": "x=%{x}<br>y=%{y}<br>f=%{z}<extra></extra>",
            }
        ],
        "layout": {
            "scene": {
                "xaxis": {"title": "x"},
                "yaxis": {"title": "y"},
                "zaxis": {"title": "f(x,y)"},
                "camera": {"eye": {"x": 1.5, "y": 1.3, "z": 0.9}},
            },
            "margin": {"l": 0, "r": 0, "t": 12, "b": 0},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
        },
        "config": {"responsive": True, "displaylogo": False},
        "meta": {
            "interactiveSurface": {
                "kind": "ab_quadratic_surface",
                "operator": operator,
                "a": {"min": a_min, "max": a_max, "step": a_step, "default": a_default},
                "b": {"min": b_min, "max": b_max, "step": b_step, "default": b_default},
            }
        },
    }
    return json.dumps(payload)


def create_paraboloid_plotly_json(title: str = "Interactive f(x, y) = x^2 + y^2") -> str:
    xs = [round(-3 + i * 0.3, 3) for i in range(21)]
    ys = [round(-3 + i * 0.3, 3) for i in range(21)]
    z = [[round(x * x + y * y, 4) for x in xs] for y in ys]
    payload = {
        "data": [
            {
                "type": "surface",
                "x": xs,
                "y": ys,
                "z": z,
                "colorscale": "Viridis",
                "showscale": True,
                "contours": {"z": {"show": True, "usecolormap": True, "highlightwidth": 1}},
            }
        ],
        "layout": {
            "title": {"text": title},
            "scene": {
                "xaxis": {"title": "x"},
                "yaxis": {"title": "y"},
                "zaxis": {"title": "f(x,y)"},
                "camera": {"eye": {"x": 1.45, "y": 1.25, "z": 0.85}},
            },
            "margin": {"l": 0, "r": 0, "t": 48, "b": 0},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
        },
        "config": {"responsive": True, "displaylogo": False},
    }
    return json.dumps(payload)


def _clean_xy_expression(expression: str) -> str:
    cleaned = expression.strip()
    cleaned = re.sub(r"^f\s*\(\s*x\s*,\s*y\s*\)\s*=\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("^", "**")
    return cleaned


def _compile_xy_expression(expression: str) -> Callable[[float, float], float]:
    source = _clean_xy_expression(expression)
    if not source:
        raise ValueError("Empty expression")

    tree = ast.parse(source, mode="eval")
    allowed_bin_ops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)
    allowed_unary_ops = (ast.UAdd, ast.USub)
    allowed_funcs: dict[str, Callable[..., Any]] = {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "exp": math.exp,
        "log": math.log,
        "abs": abs,
    }

    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.Load)):
            continue
        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, allowed_bin_ops):
                raise ValueError("Unsupported operator in expression")
            continue
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, allowed_unary_ops):
                raise ValueError("Unsupported unary operator in expression")
            continue
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in allowed_funcs:
                raise ValueError("Unsupported function in expression")
            continue
        if isinstance(node, ast.Name):
            if node.id not in {"x", "y", "pi", "e", *allowed_funcs.keys()}:
                raise ValueError("Unsupported symbol in expression")
            continue
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise ValueError("Unsupported literal type in expression")
            continue
        raise ValueError(f"Unsupported syntax node: {node.__class__.__name__}")

    compiled = compile(tree, "<xy-expression>", "eval")

    def evaluator(x: float, y: float) -> float:
        safe_locals: Dict[str, Any] = {
            "x": x,
            "y": y,
            "pi": math.pi,
            "e": math.e,
            **allowed_funcs,
        }
        value = eval(compiled, {"__builtins__": {}}, safe_locals)
        return float(value)

    return evaluator


def create_xy_surface_plotly_json(expression: str, title: str = "") -> str:
    normalized_expr = _clean_xy_expression(expression)
    if not normalized_expr:
        normalized_expr = "x**2 + y**2"

    try:
        evaluator = _compile_xy_expression(normalized_expr)
    except Exception:
        evaluator = _compile_xy_expression("x**2 + y**2")
        normalized_expr = "x**2 + y**2"

    xs = [round(-3 + i * 0.2, 3) for i in range(31)]
    ys = [round(-3 + i * 0.2, 3) for i in range(31)]
    z: List[List[float]] = []
    for y in ys:
        row: List[float] = []
        for x in xs:
            try:
                val = evaluator(x, y)
                if not math.isfinite(val):
                    val = float("nan")
            except Exception:
                val = float("nan")
            row.append(round(val, 6))
        z.append(row)

    layout: Dict[str, Any] = {
        "scene": {
            "xaxis": {"title": "x"},
            "yaxis": {"title": "y"},
            "zaxis": {"title": "f(x,y)"},
            "camera": {"eye": {"x": 1.5, "y": 1.3, "z": 0.9}},
        },
        "margin": {"l": 0, "r": 0, "t": 12, "b": 0},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
    }
    if title.strip():
        layout["title"] = {"text": title}

    payload = {
        "data": [
            {
                "type": "surface",
                "x": xs,
                "y": ys,
                "z": z,
                "colorscale": "Viridis",
                "showscale": True,
                "contours": {"z": {"show": True, "usecolormap": True, "highlightwidth": 1}},
                "hovertemplate": "x=%{x}<br>y=%{y}<br>f=%{z}<extra></extra>",
            }
        ],
        "layout": layout,
        "config": {"responsive": True, "displaylogo": False},
    }
    return json.dumps(payload)


def create_xy_surface_with_highlight_plotly_json(
    expression: str,
    *,
    point_x: float = 0.0,
    point_y: float = 0.0,
    point_label: str = "Critical point",
    title: str = "",
) -> str:
    normalized_expr = _clean_xy_expression(expression)
    if not normalized_expr:
        normalized_expr = "x**2 + y**2"

    try:
        evaluator = _compile_xy_expression(normalized_expr)
    except Exception:
        evaluator = _compile_xy_expression("x**2 + y**2")
        normalized_expr = "x**2 + y**2"

    xs = [round(-3 + i * 0.2, 3) for i in range(31)]
    ys = [round(-3 + i * 0.2, 3) for i in range(31)]
    z: List[List[float]] = []
    for y in ys:
        row: List[float] = []
        for x in xs:
            try:
                val = evaluator(x, y)
                if not math.isfinite(val):
                    val = float("nan")
            except Exception:
                val = float("nan")
            row.append(round(val, 6))
        z.append(row)

    try:
        point_z = float(evaluator(point_x, point_y))
    except Exception:
        point_z = 0.0

    layout: Dict[str, Any] = {
        "scene": {
            "xaxis": {"title": "x"},
            "yaxis": {"title": "y"},
            "zaxis": {"title": "f(x,y)"},
            "camera": {"eye": {"x": 1.5, "y": 1.3, "z": 0.9}},
            "annotations": [
                {
                    "x": point_x,
                    "y": point_y,
                    "z": point_z,
                    "text": f"{point_label} ({point_x:.1f}, {point_y:.1f}, {point_z:.1f})",
                    "showarrow": True,
                    "arrowhead": 2,
                    "ax": 18,
                    "ay": -20,
                }
            ],
        },
        "margin": {"l": 0, "r": 0, "t": 12, "b": 0},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
    }
    if title.strip():
        layout["title"] = {"text": title}

    payload = {
        "data": [
            {
                "type": "surface",
                "x": xs,
                "y": ys,
                "z": z,
                "colorscale": "Viridis",
                "showscale": True,
                "contours": {"z": {"show": True, "usecolormap": True, "highlightwidth": 1}},
                "hovertemplate": "x=%{x}<br>y=%{y}<br>f=%{z}<extra></extra>",
            },
            {
                "type": "scatter3d",
                "mode": "markers+text",
                "x": [point_x],
                "y": [point_y],
                "z": [point_z],
                "text": [point_label],
                "textposition": "top center",
                "marker": {"size": 6, "color": "#ef4444", "symbol": "diamond"},
                "hovertemplate": f"{point_label}<br>x=%{{x}}<br>y=%{{y}}<br>f=%{{z}}<extra></extra>",
            },
        ],
        "layout": layout,
        "config": {"responsive": True, "displaylogo": False},
    }
    return json.dumps(payload)


def create_chartjs_slider_fallback_html(title: str = "Interactive Function Explorer") -> str:
    safe_title = escape(title or "Interactive Function Explorer")
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{safe_title}</title>
    <style>
      :root {{
        color-scheme: light;
      }}
      body {{
        margin: 0;
        font-family: "IBM Plex Sans", system-ui, sans-serif;
        background: #f8fafc;
        color: #0f172a;
      }}
      .panel {{
        margin: 0;
        padding: 14px;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        background: #ffffff;
      }}
      .title {{
        font-size: 14px;
        font-weight: 600;
        margin: 0 0 10px 0;
      }}
      .controls {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 10px 12px;
        margin-bottom: 12px;
      }}
      .control label {{
        display: block;
        font-size: 12px;
        color: #334155;
        margin-bottom: 4px;
      }}
      .control input[type="range"] {{
        width: 100%;
      }}
      .formula {{
        font-size: 12px;
        color: #475569;
        margin-bottom: 8px;
      }}
      #chartWrap {{
        width: 100%;
        min-height: 280px;
      }}
      #chart {{
        width: 100%;
        height: 320px;
      }}
    </style>
  </head>
  <body>
    <div class="panel">
      <p class="title">{safe_title}</p>
      <div class="controls">
        <div class="control">
          <label for="a">a (quadratic term): <span id="aVal">1.00</span></label>
          <input id="a" type="range" min="-3" max="3" step="0.1" value="1" />
        </div>
        <div class="control">
          <label for="b">b (linear term): <span id="bVal">0.00</span></label>
          <input id="b" type="range" min="-6" max="6" step="0.1" value="0" />
        </div>
        <div class="control">
          <label for="c">c (constant): <span id="cVal">0.00</span></label>
          <input id="c" type="range" min="-10" max="10" step="0.1" value="0" />
        </div>
      </div>
      <div class="formula" id="formula">y = 1.00x^2 + 0.00x + 0.00</div>
      <div id="chartWrap"><canvas id="chart"></canvas></div>
    </div>

    <script src="/assets/chart.umd.js"></script>
    <script>
      const aEl = document.getElementById("a");
      const bEl = document.getElementById("b");
      const cEl = document.getElementById("c");
      const aVal = document.getElementById("aVal");
      const bVal = document.getElementById("bVal");
      const cVal = document.getElementById("cVal");
      const formula = document.getElementById("formula");
      const ctx = document.getElementById("chart").getContext("2d");

      function f(x, a, b, c) {{
        return a * x * x + b * x + c;
      }}

      const xs = [];
      for (let x = -10; x <= 10.0001; x += 0.25) {{
        xs.push(Number(x.toFixed(2)));
      }}

      function buildDataset(a, b, c) {{
        return xs.map((x) => ({{ x, y: f(x, a, b, c) }}));
      }}

      const chart = new Chart(ctx, {{
        type: "line",
        data: {{
          datasets: [{{
            label: "y = ax^2 + bx + c",
            data: buildDataset(1, 0, 0),
            borderColor: "#2563eb",
            borderWidth: 2,
            fill: false,
            pointRadius: 0,
            tension: 0.18
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          parsing: false,
          scales: {{
            x: {{
              type: "linear",
              min: -10,
              max: 10,
              grid: {{ color: "rgba(148,163,184,0.22)" }},
              title: {{ display: true, text: "x" }}
            }},
            y: {{
              grid: {{ color: "rgba(148,163,184,0.22)" }},
              title: {{ display: true, text: "y" }}
            }}
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{ mode: "nearest", intersect: false }}
          }}
        }}
      }});

      function update() {{
        const a = Number(aEl.value);
        const b = Number(bEl.value);
        const c = Number(cEl.value);
        aVal.textContent = a.toFixed(2);
        bVal.textContent = b.toFixed(2);
        cVal.textContent = c.toFixed(2);
        formula.textContent = `y = ${{a.toFixed(2)}}x^2 + ${{b.toFixed(2)}}x + ${{c.toFixed(2)}}`;
        chart.data.datasets[0].data = buildDataset(a, b, c);
        chart.update("none");
      }}

      [aEl, bEl, cEl].forEach((el) => el.addEventListener("input", update));
      update();
    </script>
  </body>
</html>"""


def create_plotly_line_fallback_json(title: str = "") -> str:
    xs = [round(-10 + i * 0.5, 3) for i in range(41)]
    ys = [round(0.15 * x * x - 0.8 * x + 1.5, 6) for x in xs]
    layout: Dict[str, Any] = {
        "margin": {"l": 48, "r": 20, "t": 12, "b": 44},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "xaxis": {"title": "x"},
        "yaxis": {"title": "y"},
    }
    if title.strip():
        layout["title"] = {"text": title}
    payload = {
        "data": [
            {
                "type": "scatter",
                "mode": "lines",
                "x": xs,
                "y": ys,
                "line": {"color": "#2563eb", "width": 2},
                "hovertemplate": "x=%{x}<br>y=%{y}<extra></extra>",
            }
        ],
        "layout": layout,
        "config": {"responsive": True, "displaylogo": False},
    }
    return json.dumps(payload)


def validate_svg(svg: str) -> Dict[str, str]:
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        return {"ok": "false", "error": f"Invalid SVG XML: {exc}"}

    if not root.tag.lower().endswith("svg"):
        return {"ok": "false", "error": "Root node is not <svg>"}
    return {"ok": "true"}


def sanitize_interactive_html(html: str) -> str:
    # Keep scripts inline only; block loading remote scripts/styles.
    no_remote_scripts = re.sub(
        r"<script[^>]+src=['\"]https?://[^>]*></script>",
        "",
        html,
        flags=re.IGNORECASE,
    )
    no_remote_styles = re.sub(
        r"<link[^>]+href=['\"]https?://[^>]*>",
        "",
        no_remote_scripts,
        flags=re.IGNORECASE,
    )
    return no_remote_styles.strip()

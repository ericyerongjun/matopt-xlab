"""
Template: generate Plotly surface JSON for f(x, y) = x^2 + y^2.
Adapt the function and ranges to the user's exact requirement.
"""

from __future__ import annotations

import json


def build_plotly_surface_payload():
    xs = [round(-3 + i * 0.3, 3) for i in range(21)]
    ys = [round(-3 + i * 0.3, 3) for i in range(21)]
    z = [[round(x * x + y * y, 4) for x in xs] for y in ys]
    return {
        "data": [
            {
                "type": "surface",
                "x": xs,
                "y": ys,
                "z": z,
                "colorscale": "Viridis",
                "showscale": True,
            }
        ],
        "layout": {
            "title": {"text": "f(x, y) = x^2 + y^2"},
            "scene": {
                "xaxis": {"title": "x"},
                "yaxis": {"title": "y"},
                "zaxis": {"title": "f(x,y)"},
            },
            "margin": {"l": 0, "r": 0, "t": 48, "b": 0},
        },
        "config": {"responsive": True, "displaylogo": False},
    }


if __name__ == "__main__":
    print(json.dumps(build_plotly_surface_payload()))

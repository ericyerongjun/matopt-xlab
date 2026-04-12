/**
 * PlotRenderer — renders Plotly charts client-side from JSON data.
 *
 * Accepts a JSON string containing { data, layout? } in Plotly format
 * and renders an interactive chart using react-plotly.js.
 */

import React, { useMemo, lazy, Suspense, memo, useEffect, useState } from "react";

// Lazy-load Plotly to avoid bloating the initial bundle (~3MB)
const Plot = lazy(() => import("react-plotly.js"));

interface Props {
    /** JSON string with Plotly { data, layout?, config? } */
    json: string;
}

interface SliderSpec {
    min: number;
    max: number;
    step: number;
    default: number;
}

interface InteractiveSurfaceMeta {
    kind: string;
    operator: "plus" | "minus";
    a: SliderSpec;
    b: SliderSpec;
}

const DEFAULT_LAYOUT: Partial<Plotly.Layout> = {
    autosize: true,
    margin: { l: 50, r: 30, t: 40, b: 50 },
    font: { family: "inherit", size: 14 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    xaxis: { gridcolor: "#e6e6f0", zeroline: false },
    yaxis: { gridcolor: "#e6e6f0", zeroline: false },
    legend: { orientation: "h", y: -0.15 },
    colorway: ["#10a37f", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6"],
};

const DEFAULT_CONFIG: Partial<Plotly.Config> = {
    responsive: true,
    displayModeBar: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
    displaylogo: false,
};

function PlotRenderer({ json }: Props) {
    const parsed = useMemo(() => {
        try {
            const obj = JSON.parse(json);
            const mergedLayout = {
                ...DEFAULT_LAYOUT,
                ...obj.layout,
                title: undefined,
            };
            const mergedConfig = {
                ...DEFAULT_CONFIG,
                ...obj.config,
                displayModeBar: false,
                displaylogo: false,
            };
            return {
                data: obj.data || [],
                layout: mergedLayout,
                config: mergedConfig,
                meta: obj.meta || {},
            };
        } catch {
            return null;
        }
    }, [json]);

    const interactiveMeta = parsed?.meta?.interactiveSurface as
        | InteractiveSurfaceMeta
        | undefined;
    const [aValue, setAValue] = useState(1);
    const [bValue, setBValue] = useState(1);

    useEffect(() => {
        if (!interactiveMeta) return;
        setAValue(interactiveMeta.a.default);
        setBValue(interactiveMeta.b.default);
    }, [json, interactiveMeta]);

    const renderBundle = useMemo(() => {
        if (!parsed) return null;
        if (!interactiveMeta || interactiveMeta.kind !== "ab_quadratic_surface") {
            return { data: parsed.data, layout: parsed.layout, config: parsed.config };
        }
        const firstTrace = parsed.data[0] ?? {};
        if (String(firstTrace.type || "").toLowerCase() !== "surface") {
            return { data: parsed.data, layout: parsed.layout, config: parsed.config };
        }
        const xs = Array.isArray(firstTrace.x) ? firstTrace.x.map((v: unknown) => Number(v)) : [];
        const ys = Array.isArray(firstTrace.y) ? firstTrace.y.map((v: unknown) => Number(v)) : [];
        if (xs.length === 0 || ys.length === 0) {
            return { data: parsed.data, layout: parsed.layout, config: parsed.config };
        }
        const sign = interactiveMeta.operator === "plus" ? 1 : -1;
        const z = ys.map((y: number) =>
            xs.map((x: number) => Number((aValue * x * x + sign * bValue * y * y).toFixed(6)))
        );
        const nextFirstTrace = {
            ...firstTrace,
            z,
            hovertemplate: "x=%{x}<br>y=%{y}<br>f=%{z}<extra></extra>",
        };
        return {
            data: [nextFirstTrace, ...parsed.data.slice(1)],
            layout: parsed.layout,
            config: parsed.config,
        };
    }, [aValue, bValue, interactiveMeta, parsed]);

    if (!renderBundle || renderBundle.data.length === 0) {
        return (
            <div className="plot-error">
                Failed to render plot — invalid data.
            </div>
        );
    }

    return (
        <div className="plot-container">
            {interactiveMeta?.kind === "ab_quadratic_surface" && (
                <div style={{ display: "grid", gap: 8, marginBottom: 10 }}>
                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                            gap: 12,
                        }}
                    >
                        <label style={{ fontSize: 13 }}>
                            a: {aValue.toFixed(2)}
                            <input
                                type="range"
                                min={interactiveMeta.a.min}
                                max={interactiveMeta.a.max}
                                step={interactiveMeta.a.step}
                                value={aValue}
                                onChange={(e) => setAValue(Number(e.target.value))}
                                style={{ width: "100%" }}
                            />
                        </label>
                        <label style={{ fontSize: 13 }}>
                            b: {bValue.toFixed(2)}
                            <input
                                type="range"
                                min={interactiveMeta.b.min}
                                max={interactiveMeta.b.max}
                                step={interactiveMeta.b.step}
                                value={bValue}
                                onChange={(e) => setBValue(Number(e.target.value))}
                                style={{ width: "100%" }}
                            />
                        </label>
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.8 }}>
                        f(x, y) = {aValue.toFixed(2)}*x^2{" "}
                        {interactiveMeta.operator === "plus" ? "+" : "-"}{" "}
                        {bValue.toFixed(2)}*y^2
                    </div>
                </div>
            )}
            <Suspense
                fallback={
                    <div style={{ padding: 24, textAlign: "center" }}>
                        Loading chart...
                    </div>
                }
            >
                <Plot
                    data={renderBundle.data}
                    layout={renderBundle.layout}
                    config={renderBundle.config}
                    useResizeHandler
                    style={{ width: "100%", height: "380px" }}
                />
            </Suspense>
        </div>
    );
}

export default memo(PlotRenderer);

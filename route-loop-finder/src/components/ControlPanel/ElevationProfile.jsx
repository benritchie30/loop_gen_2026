import { useMemo } from 'react';

const CHART_WIDTH = 280;
const CHART_HEIGHT = 120;
const PADDING = { top: 12, right: 12, bottom: 24, left: 40 };

/**
 * SVG elevation profile chart — filled area chart showing elevation over distance.
 * Takes elevation_profile array of [distance_mi, elevation_ft] from path properties.
 */
function ElevationProfile({ elevationProfile }) {
    const chartData = useMemo(() => {
        if (!elevationProfile || elevationProfile.length < 2) return null;

        const distances = elevationProfile.map(p => p[0]);
        const elevations = elevationProfile.map(p => p[1]);

        const minDist = distances[0];
        const maxDist = distances[distances.length - 1];
        const minElev = Math.min(...elevations);
        const maxElev = Math.max(...elevations);

        // Add padding to elevation range
        const elevRange = maxElev - minElev || 1;
        const elevPad = elevRange * 0.1;
        const yMin = minElev - elevPad;
        const yMax = maxElev + elevPad;

        const plotW = CHART_WIDTH - PADDING.left - PADDING.right;
        const plotH = CHART_HEIGHT - PADDING.top - PADDING.bottom;
        const distRange = maxDist - minDist || 1;

        const scaleX = (d) => PADDING.left + ((d - minDist) / distRange) * plotW;
        const scaleY = (e) => PADDING.top + plotH - ((e - yMin) / (yMax - yMin)) * plotH;

        // Build SVG path for the line
        const linePoints = elevationProfile.map(
            ([d, e]) => `${scaleX(d).toFixed(1)},${scaleY(e).toFixed(1)}`
        );
        const linePath = `M${linePoints.join('L')}`;

        // Build filled area path (line + close along bottom)
        const bottomY = PADDING.top + plotH;
        const areaPath = `${linePath}L${scaleX(maxDist).toFixed(1)},${bottomY}L${scaleX(minDist).toFixed(1)},${bottomY}Z`;

        // Y-axis ticks (3 ticks)
        const yTicks = [yMin, (yMin + yMax) / 2, yMax].map(v => ({
            y: scaleY(v),
            label: `${Math.round(v)}`
        }));

        // X-axis ticks
        const xTicks = [];
        const step = distRange > 5 ? Math.ceil(distRange / 4) : distRange > 1 ? 1 : 0.5;
        for (let d = Math.ceil(minDist / step) * step; d <= maxDist; d += step) {
            xTicks.push({
                x: scaleX(d),
                label: `${d.toFixed(step < 1 ? 1 : 0)}`
            });
        }

        return {
            linePath,
            areaPath,
            yTicks,
            xTicks,
            plotW,
            plotH,
            bottomY,
            minElev: Math.round(minElev),
            maxElev: Math.round(maxElev),
            totalGain: Math.round(maxElev - minElev)
        };
    }, [elevationProfile]);

    if (!chartData) {
        return null;
    }

    return (
        <div className="elevation-profile">
            <svg
                width={CHART_WIDTH}
                height={CHART_HEIGHT}
                viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                style={{ display: 'block', width: '100%', height: 'auto' }}
            >
                <defs>
                    <linearGradient id="elevGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.05" />
                    </linearGradient>
                </defs>

                {/* Filled area */}
                <path d={chartData.areaPath} fill="url(#elevGradient)" />

                {/* Line */}
                <path
                    d={chartData.linePath}
                    fill="none"
                    stroke="var(--color-primary)"
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                />

                {/* Y-axis ticks */}
                {chartData.yTicks.map((tick, i) => (
                    <g key={`y-${i}`}>
                        <line
                            x1={PADDING.left}
                            y1={tick.y}
                            x2={PADDING.left + chartData.plotW}
                            y2={tick.y}
                            stroke="var(--color-border)"
                            strokeWidth="0.5"
                            strokeDasharray="3,3"
                        />
                        <text
                            x={PADDING.left - 4}
                            y={tick.y + 3}
                            textAnchor="end"
                            fontSize="9"
                            fill="var(--color-text-muted)"
                        >
                            {tick.label}
                        </text>
                    </g>
                ))}

                {/* X-axis ticks */}
                {chartData.xTicks.map((tick, i) => (
                    <text
                        key={`x-${i}`}
                        x={tick.x}
                        y={chartData.bottomY + 14}
                        textAnchor="middle"
                        fontSize="9"
                        fill="var(--color-text-muted)"
                    >
                        {tick.label}
                    </text>
                ))}

                {/* X-axis label */}
                <text
                    x={PADDING.left + chartData.plotW / 2}
                    y={CHART_HEIGHT - 1}
                    textAnchor="middle"
                    fontSize="8"
                    fill="var(--color-text-muted)"
                >
                    miles
                </text>
            </svg>
        </div>
    );
}

export default ElevationProfile;

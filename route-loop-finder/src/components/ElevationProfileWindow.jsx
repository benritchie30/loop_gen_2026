import { useMemo } from 'react';
import { Minimize2, ArrowLeftRight } from 'lucide-react';
import './ElevationProfileWindow.css';

const CHART_WIDTH = 800;
const CHART_HEIGHT = 200;
const PADDING = { top: 16, right: 24, bottom: 32, left: 48 };

/**
 * Standalone window displaying elevation profile chart.
 * Centered at the bottom of the screen with larger dimensions.
 */
function ElevationProfileWindow({ elevationProfile, onClose, hoveredPoint, onHover, onFlipPath }) {
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
        const invertX = (x) => minDist + ((x - PADDING.left) / plotW) * distRange;

        // Build SVG path for the line
        const linePoints = elevationProfile.map(
            ([d, e]) => `${scaleX(d).toFixed(1)},${scaleY(e).toFixed(1)}`
        );
        const linePath = `M${linePoints.join('L')}`;

        // Build filled area path (line + close along bottom)
        const bottomY = PADDING.top + plotH;
        const areaPath = `${linePath}L${scaleX(maxDist).toFixed(1)},${bottomY}L${scaleX(minDist).toFixed(1)},${bottomY}Z`;

        // Y-axis ticks (5 ticks)
        const yTicks = [];
        for (let i = 0; i <= 4; i++) {
            const v = yMin + (yMax - yMin) * (i / 4);
            yTicks.push({
                y: scaleY(v),
                label: `${Math.round(v)}`
            });
        }

        // X-axis ticks
        const xTicks = [];
        const step = distRange > 10 ? Math.ceil(distRange / 8) : distRange > 5 ? 1 : 0.5;
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
            scaleX,
            scaleY,
            invertX,
            minDist,
            maxDist
        };
    }, [elevationProfile]);

    const handleMouseMove = (e) => {
        if (!chartData) return;
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.clientX - rect.left;

        // Convert x to distance
        let dist = chartData.invertX(x);

        // Clamp to range
        dist = Math.max(chartData.minDist, Math.min(dist, chartData.maxDist));

        // Find closest point in profile
        // Profile is sorted by distance
        let closest = elevationProfile[0];
        let minDiff = Math.abs(closest[0] - dist);

        for (let i = 1; i < elevationProfile.length; i++) {
            const diff = Math.abs(elevationProfile[i][0] - dist);
            if (diff < minDiff) {
                minDiff = diff;
                closest = elevationProfile[i];
            }
        }

        // closest format: [dist_mi, elev_ft, lat, lng, bearing]
        onHover({
            distance: closest[0],
            elevation: closest[1],
            coordinate: [closest[2], closest[3]],
            bearing: closest[4] // Optional
        });
    };

    const handleMouseLeave = () => {
        onHover(null);
    };

    if (!chartData) {
        return null;
    }

    return (
        <div className="elevation-window">
            <div className="elevation-window__content">
                <div className="elevation-window__header">
                    <h3>Elevation Profile</h3>
                    <div className="elevation-window__controls">
                        <button
                            className="elevation-window__flip-btn"
                            onClick={onFlipPath}
                            title="Flip Path Direction"
                        >
                            <ArrowLeftRight size={16} />
                            Reverse Path
                        </button>
                        <button
                            className="elevation-window__close"
                            onClick={onClose}
                            title="Minimize"
                        >
                            <Minimize2 size={18} />
                        </button>
                    </div>
                </div>
                <svg
                    width={CHART_WIDTH}
                    height={CHART_HEIGHT}
                    viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                    style={{ display: 'block', width: '100%', height: 'auto', cursor: 'crosshair' }}
                    onMouseMove={handleMouseMove}
                    onMouseLeave={handleMouseLeave}
                >
                    <defs>
                        <linearGradient id="elevGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.5" />
                            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.08" />
                        </linearGradient>
                    </defs>

                    {/* Filled area */}
                    <path d={chartData.areaPath} fill="url(#elevGradient)" />

                    {/* Grid lines */}
                    {chartData.yTicks.map((tick, i) => (
                        <line
                            key={`y-grid-${i}`}
                            x1={PADDING.left}
                            y1={tick.y}
                            x2={PADDING.left + chartData.plotW}
                            y2={tick.y}
                            stroke="var(--color-border)"
                            strokeWidth="0.5"
                            strokeDasharray="3,3"
                            opacity="0.5"
                        />
                    ))}

                    {/* Main line */}
                    <path
                        d={chartData.linePath}
                        fill="none"
                        stroke="var(--color-primary)"
                        strokeWidth="2.5"
                        strokeLinejoin="round"
                    />

                    {/* Y-axis */}
                    <line
                        x1={PADDING.left}
                        y1={PADDING.top}
                        x2={PADDING.left}
                        y2={PADDING.top + chartData.plotH}
                        stroke="var(--color-border)"
                        strokeWidth="1"
                    />

                    {/* X-axis */}
                    <line
                        x1={PADDING.left}
                        y1={chartData.bottomY}
                        x2={PADDING.left + chartData.plotW}
                        y2={chartData.bottomY}
                        stroke="var(--color-border)"
                        strokeWidth="1"
                    />

                    {/* Y-axis ticks */}
                    {chartData.yTicks.map((tick, i) => (
                        <g key={`y-${i}`}>
                            <line
                                x1={PADDING.left - 4}
                                y1={tick.y}
                                x2={PADDING.left}
                                y2={tick.y}
                                stroke="var(--color-border)"
                                strokeWidth="1"
                            />
                            <text
                                x={PADDING.left - 8}
                                y={tick.y + 4}
                                textAnchor="end"
                                fontSize="11"
                                fill="var(--color-text-muted)"
                            >
                                {tick.label}
                            </text>
                        </g>
                    ))}

                    {/* X-axis ticks */}
                    {chartData.xTicks.map((tick, i) => (
                        <g key={`x-${i}`}>
                            <line
                                x1={tick.x}
                                y1={chartData.bottomY}
                                x2={tick.x}
                                y2={chartData.bottomY + 4}
                                stroke="var(--color-border)"
                                strokeWidth="1"
                            />
                            <text
                                x={tick.x}
                                y={chartData.bottomY + 18}
                                textAnchor="middle"
                                fontSize="11"
                                fill="var(--color-text-muted)"
                            >
                                {tick.label}
                            </text>
                        </g>
                    ))}

                    {/* Hover Indicator */}
                    {hoveredPoint && (
                        <g>
                            <line
                                x1={chartData.scaleX(hoveredPoint.distance)}
                                y1={PADDING.top}
                                x2={chartData.scaleX(hoveredPoint.distance)}
                                y2={chartData.bottomY}
                                stroke="var(--color-accent)"
                                strokeWidth="1"
                                strokeDasharray="4,2"
                            />
                            <circle
                                cx={chartData.scaleX(hoveredPoint.distance)}
                                cy={chartData.scaleY(hoveredPoint.elevation)}
                                r="4"
                                fill="white"
                                stroke="var(--color-accent)"
                                strokeWidth="2"
                            />
                            <text
                                x={Math.min(chartData.scaleX(hoveredPoint.distance) + 8, CHART_WIDTH - 60)}
                                y={Math.max(chartData.scaleY(hoveredPoint.elevation) - 8, PADDING.top + 10)}
                                fontSize="11"
                                fontWeight="bold"
                                fill="var(--color-text)"
                                stroke="var(--bg-color)"
                                strokeWidth="3"
                                paintOrder="stroke"
                            >
                                {hoveredPoint.elevation} ft
                            </text>
                        </g>
                    )}

                    {/* Axis labels */}
                    <text
                        x={PADDING.left + chartData.plotW / 2}
                        y={CHART_HEIGHT - 6}
                        textAnchor="middle"
                        fontSize="12"
                        fill="var(--color-text-muted)"
                    >
                        Distance (miles)
                    </text>

                    <text
                        x={16}
                        y={PADDING.top + chartData.plotH / 2}
                        textAnchor="middle"
                        fontSize="12"
                        fill="var(--color-text-muted)"
                        transform={`rotate(-90 16 ${PADDING.top + chartData.plotH / 2})`}
                    >
                        Elevation (feet)
                    </text>
                </svg>
            </div>
        </div>
    );
}

export default ElevationProfileWindow;

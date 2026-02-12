import { useCallback, useState } from 'react';

const MIN_DISTANCE = 0;
const MAX_DISTANCE = 100;

/**
 * Dual-handle range slider for filtering paths by distance.
 * Uses a custom approach with two range inputs overlaid.
 */
function DistanceFilter({ distanceRange, setDistanceRange }) {
    const [minVal, maxVal] = distanceRange;

    const handleMinChange = useCallback((e) => {
        const value = Math.min(Number(e.target.value), maxVal - 1);
        setDistanceRange([value, maxVal]);
    }, [maxVal, setDistanceRange]);

    const handleMaxChange = useCallback((e) => {
        const value = Math.max(Number(e.target.value), minVal + 1);
        setDistanceRange([minVal, value]);
    }, [minVal, setDistanceRange]);

    // Calculate the filled track position
    const minPercent = ((minVal - MIN_DISTANCE) / (MAX_DISTANCE - MIN_DISTANCE)) * 100;
    const maxPercent = ((maxVal - MIN_DISTANCE) / (MAX_DISTANCE - MIN_DISTANCE)) * 100;

    return (
        <div className="distance-filter">
            <div className="distance-filter__header">
                <span className="distance-filter__range">
                    {minVal} – {maxVal} miles
                </span>
            </div>

            <div className="distance-filter__slider-container">
                {/* Custom track to show selected range */}
                <div
                    style={{
                        position: 'absolute',
                        top: '50%',
                        left: `${minPercent}%`,
                        width: `${maxPercent - minPercent}%`,
                        height: '6px',
                        background: 'var(--color-primary)',
                        borderRadius: '3px',
                        transform: 'translateY(-50%)',
                        pointerEvents: 'none',
                        zIndex: 1
                    }}
                />

                {/* Min slider */}
                <input
                    type="range"
                    min={MIN_DISTANCE}
                    max={MAX_DISTANCE}
                    value={minVal}
                    onChange={handleMinChange}
                    className="distance-filter__slider"
                    style={{
                        position: 'absolute',
                        width: '100%',
                        pointerEvents: 'auto',
                        zIndex: 2
                    }}
                    aria-label="Minimum distance"
                />

                {/* Max slider */}
                <input
                    type="range"
                    min={MIN_DISTANCE}
                    max={MAX_DISTANCE}
                    value={maxVal}
                    onChange={handleMaxChange}
                    className="distance-filter__slider"
                    style={{
                        position: 'relative',
                        width: '100%',
                        pointerEvents: 'auto',
                        zIndex: 3
                    }}
                    aria-label="Maximum distance"
                />
            </div>

            <div className="distance-filter__marks">
                <span>0mi</span>
                <span>50mi</span>
                <span>100mi</span>
            </div>
        </div>
    );
}

export default DistanceFilter;

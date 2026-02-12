import { useCallback } from 'react';

const MIN_DIFFICULTY = 1;
const MAX_DIFFICULTY = 10;

/**
 * Dual-handle range slider for filtering paths by difficulty (1-10 scale).
 */
function DifficultyFilter({ difficultyRange, setDifficultyRange }) {
    const [minVal, maxVal] = difficultyRange;

    const handleMinChange = useCallback((e) => {
        const value = Math.min(Number(e.target.value), maxVal - 1);
        setDifficultyRange([Math.max(value, MIN_DIFFICULTY), maxVal]);
    }, [maxVal, setDifficultyRange]);

    const handleMaxChange = useCallback((e) => {
        const value = Math.max(Number(e.target.value), minVal + 1);
        setDifficultyRange([minVal, Math.min(value, MAX_DIFFICULTY)]);
    }, [minVal, setDifficultyRange]);

    const minPercent = ((minVal - MIN_DIFFICULTY) / (MAX_DIFFICULTY - MIN_DIFFICULTY)) * 100;
    const maxPercent = ((maxVal - MIN_DIFFICULTY) / (MAX_DIFFICULTY - MIN_DIFFICULTY)) * 100;

    return (
        <div className="distance-filter">
            <div className="distance-filter__header">
                <span className="distance-filter__range">
                    {minVal} – {maxVal}
                </span>
            </div>

            <div className="distance-filter__slider-container">
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

                <input
                    type="range"
                    min={MIN_DIFFICULTY}
                    max={MAX_DIFFICULTY}
                    step={1}
                    value={minVal}
                    onChange={handleMinChange}
                    className="distance-filter__slider"
                    style={{
                        position: 'absolute',
                        width: '100%',
                        pointerEvents: 'auto',
                        zIndex: 2
                    }}
                    aria-label="Minimum difficulty"
                />

                <input
                    type="range"
                    min={MIN_DIFFICULTY}
                    max={MAX_DIFFICULTY}
                    step={1}
                    value={maxVal}
                    onChange={handleMaxChange}
                    className="distance-filter__slider"
                    style={{
                        position: 'relative',
                        width: '100%',
                        pointerEvents: 'auto',
                        zIndex: 3
                    }}
                    aria-label="Maximum difficulty"
                />
            </div>

            <div className="distance-filter__marks">
                <span>1</span>
                <span>5</span>
                <span>10</span>
            </div>
        </div>
    );
}

export default DifficultyFilter;

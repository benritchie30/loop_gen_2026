import { ChevronLeft, ChevronRight, MapPin, MousePointer2, Pencil, Undo2, Ban, ArrowUpDown } from 'lucide-react';
import './ControlPanel.css';

import PathInfo from './PathInfo';
import DistanceFilter from './DistanceFilter';
import DifficultyFilter from './DifficultyFilter';
import GraphSelector from './GraphSelector';

/**
 * Floating control panel for path navigation, filtering, and mode switching.
 */
function ControlPanel({
    mode,
    setMode,
    currentPath,
    currentPathIndex,
    filteredPathsCount,
    totalPathsCount,
    distanceRange,
    setDistanceRange,
    difficultyRange,
    setDifficultyRange,
    sortBy,
    setSortBy,
    sortAscending,
    setSortAscending,
    onNextPath,
    onPrevPath,
    hasActivePathSet,
    activeTool,
    setActiveTool,
    isExcludeMode,
    setIsExcludeMode,
    onUndo,
    genSettings,
    setGenSettings,
    graphs,
    activeGraph,
    onSwitchGraph,
    onStartGraphCreate,
    isCreatingGraph,
    graphCreateMode,
    setGraphCreateMode,
    graphBounds
}) {
    const canGoPrev = currentPathIndex > 0;
    const canGoNext = currentPathIndex < filteredPathsCount - 1;

    const handleSettingChange = (e) => {
        const { name, value, type } = e.target;
        setGenSettings(prev => ({
            ...prev,
            [name]: type === 'number' ? parseFloat(value) : value
        }));
    };

    return (
        <div className="control-panel">
            {/* Header with navigation - only show in display mode */}
            {mode === 'display' && (
                <div className="control-panel__header">
                    <div className="control-panel__nav">
                        <button
                            className="control-panel__nav-btn"
                            onClick={onPrevPath}
                            disabled={!canGoPrev}
                            aria-label="Previous path"
                        >
                            <ChevronLeft size={20} />
                        </button>
                        <button
                            className="control-panel__nav-btn"
                            onClick={onNextPath}
                            disabled={!canGoNext}
                            aria-label="Next path"
                        >
                            <ChevronRight size={20} />
                        </button>
                    </div>

                    <div className="control-panel__counter">
                        {filteredPathsCount > 0 ? (
                            <>
                                <strong>{currentPathIndex + 1}</strong> / {filteredPathsCount}
                                {filteredPathsCount !== totalPathsCount && (
                                    <span> ({totalPathsCount})</span>
                                )}
                            </>
                        ) : (
                            <span>No paths</span>
                        )}
                    </div>
                </div>
            )}

            <div className="control-panel__body">
                {/* Graph selector - only in input mode */}
                {(mode === 'input' || mode === 'graphCreate') && (
                    <div className="control-panel__section">
                        <GraphSelector
                            graphs={graphs}
                            activeGraph={activeGraph}
                            onSwitchGraph={onSwitchGraph}
                            onStartGraphCreate={onStartGraphCreate}
                            isCreatingGraph={isCreatingGraph}
                            isGraphCreateMode={mode === 'graphCreate'}
                            graphCreateMode={graphCreateMode}
                            setGraphCreateMode={setGraphCreateMode}
                            graphBounds={graphBounds}
                        />
                    </div>
                )}

                {/* Generator Settings - Show in INPUT mode */}
                {mode === 'input' && genSettings && (
                    <div className="control-panel__section">
                        <div className="control-panel__section-title">Generation Settings</div>
                        <div className="settings-grid">
                            <label className="setting-item">
                                <span>Min Miles</span>
                                <input
                                    type="number"
                                    name="min_path_len"
                                    value={genSettings.min_path_len}
                                    onChange={handleSettingChange}
                                    min="1" max="100"
                                />
                            </label>
                            <label className="setting-item">
                                <span>Max Miles</span>
                                <input
                                    type="number"
                                    name="max_path_len"
                                    value={genSettings.max_path_len}
                                    onChange={handleSettingChange}
                                    min="1" max="200"
                                />
                            </label>
                            <label className="setting-item">
                                <span>Ratio</span>
                                <input
                                    type="number"
                                    name="loop_ratio"
                                    value={genSettings.loop_ratio}
                                    onChange={handleSettingChange}
                                    step="0.1" min="0" max="1"
                                />
                            </label>
                            <label className="setting-item">
                                <span>path_sim</span>
                                <input
                                    type="number"
                                    name="sim_ceiling"
                                    value={genSettings.sim_ceiling}
                                    onChange={handleSettingChange}
                                    step="0.1" min="0" max="1"
                                />
                            </label>
                            <label className="setting-item">
                                <span>Count</span>
                                <input
                                    type="number"
                                    name="num_paths"
                                    value={genSettings.num_paths}
                                    onChange={handleSettingChange}
                                    min="1" max="100"
                                />
                            </label>

                            <label className="setting-item full-width">
                                <span>Dedup</span>
                                <select
                                    name="deduplication"
                                    value={genSettings.deduplication}
                                    onChange={handleSettingChange}
                                >
                                    <option value="centroid">Centroid (Spatial)</option>
                                    <option value="jaccard">Jaccard (Overlap)</option>
                                </select>
                            </label>
                            {genSettings.deduplication === 'centroid' && (
                                <label className="setting-item full-width">
                                    <span>Dist (m)</span>
                                    <input
                                        type="number"
                                        name="min_dist_m"
                                        value={genSettings.min_dist_m || 50}
                                        onChange={handleSettingChange}
                                        min="10" max="1000" step="10"
                                    />
                                </label>
                            )}
                        </div>
                    </div>
                )}

                {/* Drawing Tools - Only show in display mode */}
                {mode === 'display' && (
                    <div className="control-panel__section">
                        <div className="control-panel__section-title">Tools</div>
                        <div className="control-panel__tools">
                            <button
                                className={`control-panel__tool-btn ${activeTool === 'path' ? 'active' : ''}`}
                                onClick={() => setActiveTool(activeTool === 'path' ? null : 'path')}
                                title="Path Tool (Select Along Road)"
                            >
                                <Pencil size={18} />
                            </button>
                            <button
                                className={`control-panel__tool-btn ${activeTool === 'lasso' ? 'active' : ''}`}
                                onClick={() => setActiveTool(activeTool === 'lasso' ? null : 'lasso')}
                                title="Lasso Tool (Select Area)"
                            >
                                <MousePointer2 size={18} />
                            </button>
                            <button
                                className={`control-panel__tool-btn ${isExcludeMode ? 'active exclude' : ''}`}
                                onClick={() => setIsExcludeMode(!isExcludeMode)}
                                title="Toggle Exclude Mode (Hold 'd')"
                            >
                                <Ban size={18} />
                            </button>
                            <button
                                className="control-panel__tool-btn"
                                onClick={onUndo}
                                title="Undo Last Selection (z)"
                            >
                                <Undo2 size={18} />
                            </button>
                        </div>
                    </div>
                )}

                {/* Path info - only show when we have a path */}
                {hasActivePathSet && (
                    <>
                        <div className="control-panel__section">
                            <div className="control-panel__section-title">Sort By</div>
                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                <select
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value)}
                                    className="control-panel__select"
                                    style={{ flex: 1 }}
                                >
                                    <option value="total_miles">Distance</option>
                                    <option value="difficulty">Difficulty</option>
                                    <option value="total_climb_ft">Climbing</option>
                                    <option value="loop_ratio">Loop Ratio</option>
                                    <option value="turns">Turns</option>
                                    <option value="spatial">Spatial Flow</option>
                                </select>
                                <button
                                    className="control-panel__tool-btn"
                                    onClick={() => setSortAscending(!sortAscending)}
                                    title={sortAscending ? 'Ascending' : 'Descending'}
                                    style={{ minWidth: '32px' }}
                                >
                                    <ArrowUpDown size={16} />
                                </button>
                            </div>
                        </div>

                        <div className="control-panel__section">
                            <div className="control-panel__section-title">Filter by Distance</div>
                            <DistanceFilter
                                distanceRange={distanceRange}
                                setDistanceRange={setDistanceRange}
                            />
                        </div>

                        <div className="control-panel__section">
                            <div className="control-panel__section-title">Filter by Difficulty</div>
                            <DifficultyFilter
                                difficultyRange={difficultyRange}
                                setDifficultyRange={setDifficultyRange}
                            />
                        </div>
                    </>
                )}

                {/* Path info - only show when we have a path */}
                {currentPath ? (
                    <div className="control-panel__section">
                        <div className="control-panel__section-title">Path Details</div>
                        <PathInfo path={currentPath} />
                    </div>
                ) : hasActivePathSet ? (
                    <div className="control-panel__empty">
                        <div className="control-panel__empty-text">
                            No paths match your filters
                        </div>
                    </div>
                ) : null}
            </div>
        </div>
    );
}

export default ControlPanel;

import { MapContainer, TileLayer, Rectangle, Polygon, Circle } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './MapView.css';

import MapClickHandler from './MapClickHandler';
import DrawingHandler from './DrawingHandler';
import PathMarker from './PathMarker';
import PathRenderer from './PathRenderer';
import BoundsSelector from './BoundsSelector';

const DEFAULT_CENTER = [35.626288, -82.551141]; // Default to Asheville area
const DEFAULT_ZOOM = 13;

/**
 * Main map view component - renders the Leaflet map and all map-based UI.
 */
function MapView({
    mode, // 'input', 'display', or 'graphCreate'
    activeTool, // 'path', 'lasso', or null
    isExcludeMode, // boolean
    wsStatus,
    pendingMarker,
    pathSetMarkers,
    activePathSetId,
    currentPath,
    filteredPaths,
    drawnSelections,
    onMapClick,
    onMarkerClick,
    onDrawingComplete,
    graphBounds,
    onGraphBoundsChange,
    graphCreateMode,
    graphBoundaries,
    activeGraph,
    pathUndoRef
}) {
    const getSavedPosition = () => {
        try {
            const saved = localStorage.getItem('lastMapPosition');
            if (saved) {
                const { center, zoom } = JSON.parse(saved);
                return { center, zoom };
            }
        } catch (e) {
            console.warn('Failed to load saved map position');
        }
        return { center: DEFAULT_CENTER, zoom: DEFAULT_ZOOM };
    };

    const { center, zoom } = getSavedPosition();

    const getHintText = () => {
        if (mode === 'input') {
            if (pendingMarker) {
                return 'Press Enter to generate routes from this point';
            }
            return null;
        }
        if (mode === 'graphCreate') {
            if (graphCreateMode === 'polygon') {
                return 'Click to add polygon vertices, then press Enter';
            }
            if (graphCreateMode === 'circle') {
                return 'Drag center pin and radius handle, then press Enter';
            }
            return 'Drag the markers to set graph bounds, then press Enter';
        }
        if (activeTool) {
            const modeText = isExcludeMode ? 'EXCLUDE' : 'INCLUDE';
            if (activeTool === 'path') return `Click to build path (${modeText}). Ctrl+click = new start`;
            if (activeTool === 'lasso') return `Click and drag to select area to ${modeText}`;
        }
        return null;
    };

    const hintText = getHintText();

    const getModeLabel = () => {
        if (mode === 'display') {
            return activeTool ? `TOOL: ${activeTool.toUpperCase()}` : 'DISPLAY';
        }
        if (mode === 'graphCreate') return 'GRAPH CREATE';
        return mode;
    };

    // Get boundary for active graph preview
    const activeBoundary = (mode === 'input' && activeGraph && graphBoundaries)
        ? graphBoundaries[activeGraph]
        : null;

    const boundaryPreviewStyle = {
        color: '#4CAF50',
        weight: 2,
        fillColor: '#4CAF50',
        fillOpacity: 0.04,
        dashArray: '6, 4'
    };

    return (
        <div className="map-view">
            {/* Connection status */}
            <div className="map-view__status">
                <div className={`map-view__status-dot map-view__status-dot--${wsStatus}`} />
                <span>{wsStatus === 'connected' ? 'Connected' : wsStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}</span>
            </div>

            {/* Mode indicator */}
            <div className={`map-view__mode map-view__mode--${mode}`}>
                {getModeLabel()}
                {isExcludeMode && <span style={{ color: '#ff4444', marginLeft: '8px' }}>(EXCLUDE)</span>}
            </div>

            {/* Instruction hint */}
            <div className={`map-view__hint ${hintText ? 'map-view__hint--visible' : ''}`}>
                {hintText}
            </div>

            <MapContainer
                center={center}
                zoom={zoom}
                style={{ height: '100%', width: '100%' }}
                zoomControl={true}
            >
                {/* Light, minimal tile layer */}
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
                />

                {/* Click handler for input mode */}
                <MapClickHandler mode={mode} onMapClick={onMapClick} />

                {/* Drawing handler for selection mode */}
                <DrawingHandler
                    activeTool={activeTool}
                    isExcludeMode={isExcludeMode}
                    onDrawingComplete={onDrawingComplete}
                    onPathPointUndo={pathUndoRef}
                />

                {/* Pending marker (blue) - shown while user is picking a spot */}
                {pendingMarker && mode === 'input' && (
                    <PathMarker
                        position={pendingMarker}
                        color="pending"
                    />
                )}

                {/* 
                    Path Set Markers Logic:
                    - In 'input' mode: Show ALL markers (grey/inactive).
                    - In 'display' mode: Show ONLY the active marker (green/active).
                */}
                {pathSetMarkers.map(marker => {
                    const shouldShow = mode === 'input' || (mode === 'display' && marker.id === activePathSetId);

                    if (!shouldShow) return null;

                    return (
                        <PathMarker
                            key={marker.id}
                            position={marker.position}
                            color={marker.isActive ? 'active' : 'inactive'}
                            onClick={() => onMarkerClick(marker.id)}
                        />
                    );
                })}

                {/* Path rendering */}
                {mode === 'display' && activePathSetId && (
                    <PathRenderer
                        currentPath={currentPath}
                        filteredPaths={filteredPaths}
                        drawnSelections={drawnSelections}
                    />
                )}

                {/* Bounds selector for graph creation */}
                {mode === 'graphCreate' && (
                    <BoundsSelector
                        bounds={graphBounds}
                        onBoundsChange={onGraphBoundsChange}
                        boundaryMode={graphCreateMode}
                    />
                )}

                {/* Active graph boundary preview */}
                {activeBoundary && activeBoundary.type === 'box' && (
                    <Rectangle
                        bounds={[
                            [activeBoundary.south, activeBoundary.west],
                            [activeBoundary.north, activeBoundary.east]
                        ]}
                        pathOptions={boundaryPreviewStyle}
                    />
                )}
                {activeBoundary && activeBoundary.type === 'polygon' && (
                    <Polygon
                        positions={activeBoundary.coordinates.map(([lat, lng]) => [lat, lng])}
                        pathOptions={boundaryPreviewStyle}
                    />
                )}
                {activeBoundary && activeBoundary.type === 'circle' && (
                    <Circle
                        center={[activeBoundary.center[0], activeBoundary.center[1]]}
                        radius={activeBoundary.radius_miles * 1609.34}
                        pathOptions={boundaryPreviewStyle}
                    />
                )}
            </MapContainer>
        </div>
    );
}

export default MapView;


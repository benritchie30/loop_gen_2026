import { GeoJSON, CircleMarker } from 'react-leaflet';
import { useMemo } from 'react';
import DirectionArrows from './DirectionArrows';

/**
 * Renders paths on the map.
 * - Active path: bold dark navy line (always on top)
 * - Filtered paths: subtle translucent preview
 * - Drawn selections: muted amber highlight
 * - Direction arrows: small rotated arrows along the active path
 * - Centroid: small red dot (for spatial sort testing)
 * 
 * Render order ensures active path is always visible above others.
 */
function PathRenderer({ currentPath, filteredPaths, drawnSelections }) {
    // Style for inactive/background paths — very subtle so they don't clash when stacking
    const inactiveStyle = useMemo(() => ({
        weight: 2,
        color: '#7a99be',
        opacity: 0.4
    }), []);

    // Style for the currently selected path — bold dark navy, slightly transparent
    const activeStyle = useMemo(() => ({
        weight: 4,
        color: '#1e3a5f',
        opacity: 0.85
    }), []);

    // Style for drawn selection highlights — bright orange, wide, on top
    const selectionStyle = useMemo(() => ({
        weight: 8,
        color: '#ff8c42',
        opacity: 0.75
    }), []);

    // Style for exclude selections — bright red
    const excludeStyle = useMemo(() => ({
        weight: 8,
        color: '#e74c3c',
        opacity: 0.7
    }), []);

    // Generate unique keys for GeoJSON components
    const getPathKey = (path, index, prefix) => {
        const visited = path?.properties?.visited || index;
        return `${prefix}-${visited}-${index}`;
    };

    // Get style for a selection based on its type
    const getSelectionStyle = (selection) => {
        const props = selection.properties || selection;
        return props.type === 'exclude' ? excludeStyle : selectionStyle;
    };

    return (
        <>
            {/* All filtered paths — translucent preview, bottom layer */}
            {filteredPaths?.map((path, index) => {
                if (path === currentPath) return null;

                return (
                    <GeoJSON
                        key={getPathKey(path, index, 'inactive')}
                        data={path}
                        style={inactiveStyle}
                    />
                );
            })}

            {/* Current/active path — middle layer */}
            {currentPath && (
                <GeoJSON
                    key={getPathKey(currentPath, 0, 'active')}
                    data={currentPath}
                    style={activeStyle}
                />
            )}

            {/* Direction arrows along the active path */}
            {currentPath?.properties?.elevation_profile?.length > 1 && (
                <DirectionArrows
                    elevationProfile={currentPath.properties.elevation_profile}
                />
            )}

            {/* Centroid marker (for spatial sort verification) */}
            {currentPath?.properties?.centroid && (
                <CircleMarker
                    center={currentPath.properties.centroid}
                    radius={4}
                    pathOptions={{ color: 'red', fillColor: '#f00', fillOpacity: 0.8, weight: 1 }}
                    interactive={false}
                />
            )}

            {/* Drawn selections — TOP layer, always visible */}
            {drawnSelections?.map((selection, index) => (
                <GeoJSON
                    key={`selection-${index}`}
                    data={selection}
                    style={getSelectionStyle(selection)}
                />
            ))}
        </>
    );
}

export default PathRenderer;

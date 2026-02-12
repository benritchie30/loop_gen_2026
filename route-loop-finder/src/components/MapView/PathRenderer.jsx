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
function PathRenderer({
    currentPath,
    filteredPaths,
    drawnSelections,
    backgroundPane = 'overlayPane',
    activePane = 'overlayPane',
    selectionPane = 'overlayPane',
    showArrows = true,
    showCentroids = false,
    primaryColor = 215,
    hoveredPoint,
    onHover
}) {
    // Style for inactive/background paths — very subtle, matching the theme but desaturated/lighter
    const inactiveStyle = useMemo(() => ({
        weight: 2,
        color: `hsl(${primaryColor}, 40%, 65%)`, // Muted version of theme color
        opacity: 0.4
    }), [primaryColor]);

    // Style for the currently selected path — bold, using theme color
    const activeStyle = useMemo(() => ({
        weight: 4,
        color: `hsl(${primaryColor}, 65%, 30%)`, // Darker version for high contrast
        opacity: 0.85
    }), [primaryColor]);

    // Derived colors for elements
    const arrowColor = `hsl(${primaryColor}, 70%, 50%)`; // Bright theme color for arrows
    const centroidColor = `hsl(${primaryColor}, 80%, 45%)`; // Slightly different shade for centroid

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

    // Handle mouse move on the active path
    const onActivePathTarget = (feature, layer) => {
        layer.on({
            mousemove: (e) => {
                if (!currentPath?.properties?.elevation_profile) return;

                const { lat, lng } = e.latlng;
                const profile = currentPath.properties.elevation_profile;

                // Find closest point in profile to mouse position
                // Profile items: [dist_mi, elev_ft, lat, lng, bearing]
                // Simple Euclidean distance check on lat/lng
                // Since profile points are dense (every ~50m), this is reasonably accurate for hover

                let closest = profile[0];
                let minSqDist = Infinity;

                for (let i = 0; i < profile.length; i++) {
                    const p = profile[i];
                    // Skip if no coords
                    if (p.length < 4) continue;

                    const dLat = p[2] - lat;
                    const dLng = p[3] - lng;
                    const sqDist = dLat * dLat + dLng * dLng;

                    if (sqDist < minSqDist) {
                        minSqDist = sqDist;
                        closest = p;
                    }
                }

                if (closest) {
                    onHover({
                        distance: closest[0],
                        elevation: closest[1],
                        coordinate: [closest[2], closest[3]],
                        bearing: closest[4]
                    });
                }
            },
            mouseout: () => {
                onHover(null);
            }
        });
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
                        pane={backgroundPane}
                    />
                );
            })}

            {/* Current/active path — middle layer */}
            {currentPath && (
                <GeoJSON
                    key={getPathKey(currentPath, 0, 'active')}
                    data={currentPath}
                    style={activeStyle}
                    pane={activePane}
                    onEachFeature={onActivePathTarget}
                />
            )}

            {/* Direction arrows along the active path */}
            {showArrows && currentPath?.properties?.elevation_profile?.length > 1 && (
                <DirectionArrows
                    elevationProfile={currentPath.properties.elevation_profile}
                    color={arrowColor}
                />
            )}

            {/* Centroid marker (for spatial sort verification) */}
            {showCentroids && currentPath?.properties?.centroid && (
                <CircleMarker
                    center={currentPath.properties.centroid}
                    radius={4}
                    pathOptions={{
                        color: centroidColor,
                        fillColor: centroidColor,
                        fillOpacity: 0.8,
                        weight: 1
                    }}
                    interactive={false}
                />
            )}

            {/* Hovered Point Marker */}
            {hoveredPoint && hoveredPoint.coordinate && (
                <CircleMarker
                    center={hoveredPoint.coordinate}
                    radius={6}
                    pathOptions={{
                        color: 'white',
                        fillColor: `hsl(${primaryColor}, 70%, 50%)`,
                        fillOpacity: 1,
                        weight: 2
                    }}
                    interactive={false}
                    pane={activePane} // Draw on top of path
                />
            )}

            {/* Drawn selections — TOP layer, always visible */}
            {drawnSelections?.map((selection, index) => (
                <GeoJSON
                    key={`selection-${index}`}
                    data={selection}
                    style={getSelectionStyle(selection)}
                    pane={selectionPane}
                />
            ))}
        </>
    );
}

export default PathRenderer;

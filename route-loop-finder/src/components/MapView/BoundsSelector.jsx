import { useState, useRef, useEffect, useCallback } from 'react';
import { Marker, Rectangle, Polygon, Polyline, Circle, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';

// Custom marker icons for the corner handles
const createCornerIcon = (label) => L.divIcon({
    className: 'bounds-marker',
    html: `<div class="bounds-marker__inner">${label}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14]
});

const nwIcon = createCornerIcon('⬉');
const seIcon = createCornerIcon('⬊');

const centerIcon = L.divIcon({
    className: 'bounds-marker',
    html: '<div class="bounds-marker__inner" style="font-size:14px;">⊕</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14]
});

const radiusIcon = L.divIcon({
    className: 'bounds-marker',
    html: '<div class="bounds-marker__inner" style="width:20px;height:20px;font-size:11px;">↔</div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10]
});

const vertexIcon = L.divIcon({
    className: 'bounds-marker',
    html: '<div class="bounds-marker__inner" style="width:20px;height:20px;font-size:11px;">●</div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10]
});

/**
 * Haversine distance between two lat/lng points in miles.
 */
function haversineMiles(lat1, lng1, lat2, lng2) {
    const R = 3958.8; // Earth radius in miles
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Map overlay for selecting graph boundary.
 * Supports three modes: "box", "polygon", "circle"
 */
function BoundsSelector({ bounds, onBoundsChange, boundaryMode }) {
    const map = useMap();

    // Initialize bounds for each mode at current map viewport if not set
    useEffect(() => {
        if (boundaryMode === 'box' && !bounds) {
            const mapBounds = map.getBounds();
            const center = mapBounds.getCenter();
            const latSpan = (mapBounds.getNorth() - mapBounds.getSouth()) * 0.3;
            const lngSpan = (mapBounds.getEast() - mapBounds.getWest()) * 0.3;

            onBoundsChange({
                type: 'box',
                nw: { lat: center.lat + latSpan, lng: center.lng - lngSpan },
                se: { lat: center.lat - latSpan, lng: center.lng + lngSpan }
            });
        }
        if (boundaryMode === 'polygon' && !bounds) {
            onBoundsChange({
                type: 'polygon',
                coordinates: []
            });
        }
        if (boundaryMode === 'circle' && !bounds) {
            const center = map.getCenter();
            onBoundsChange({
                type: 'circle',
                center: { lat: center.lat, lng: center.lng },
                radiusMiles: 3
            });
        }
    }, [map, bounds, onBoundsChange, boundaryMode]);

    if (!bounds) return null;

    // Guard: if bounds.type doesn't match current mode, wait for reset
    if (bounds.type && bounds.type !== boundaryMode) return null;

    if (boundaryMode === 'box') {
        return <BoxSelector bounds={bounds} onBoundsChange={onBoundsChange} />;
    }

    if (boundaryMode === 'circle') {
        return <CircleSelector bounds={bounds} onBoundsChange={onBoundsChange} />;
    }

    return <PolygonSelector bounds={bounds} onBoundsChange={onBoundsChange} />;
}

/**
 * Box mode: NW/SE draggable markers + rectangle preview
 */
function BoxSelector({ bounds, onBoundsChange }) {
    const { nw, se } = bounds;

    // Rectangle bounds for Leaflet: [[south, west], [north, east]]
    const rectBounds = [
        [se.lat, nw.lng],
        [nw.lat, se.lng]
    ];

    const handleNWDrag = (e) => {
        const { lat, lng } = e.target.getLatLng();
        onBoundsChange({ type: 'box', nw: { lat, lng }, se: bounds.se });
    };

    const handleSEDrag = (e) => {
        const { lat, lng } = e.target.getLatLng();
        onBoundsChange({ type: 'box', nw: bounds.nw, se: { lat, lng } });
    };

    return (
        <>
            <Rectangle
                bounds={rectBounds}
                pathOptions={{
                    color: '#2196F3',
                    weight: 3,
                    fillColor: '#2196F3',
                    fillOpacity: 0.15,
                    dashArray: '8, 6'
                }}
            />
            <Marker
                position={[nw.lat, nw.lng]}
                icon={nwIcon}
                draggable={true}
                eventHandlers={{
                    drag: handleNWDrag,
                    dragend: handleNWDrag
                }}
            />
            <Marker
                position={[se.lat, se.lng]}
                icon={seIcon}
                draggable={true}
                eventHandlers={{
                    drag: handleSEDrag,
                    dragend: handleSEDrag
                }}
            />
        </>
    );
}

/**
 * Circle mode: Draggable center marker + radius handle on the east edge
 */
function CircleSelector({ bounds, onBoundsChange }) {
    const { center, radiusMiles } = bounds;
    const radiusMeters = radiusMiles * 1609.34;

    // Place the radius handle to the east of the center
    // Approx: 1 degree lng ≈ 69 * cos(lat) miles
    const radiusHandleLng = center.lng + radiusMiles / (69.0 * Math.cos(center.lat * Math.PI / 180));

    const handleCenterDrag = (e) => {
        const { lat, lng } = e.target.getLatLng();
        onBoundsChange({ type: 'circle', center: { lat, lng }, radiusMiles });
    };

    const handleRadiusDrag = (e) => {
        const { lat, lng } = e.target.getLatLng();
        const newRadius = haversineMiles(center.lat, center.lng, lat, lng);
        onBoundsChange({ type: 'circle', center, radiusMiles: Math.max(0.1, newRadius) });
    };

    return (
        <>
            <Circle
                center={[center.lat, center.lng]}
                radius={radiusMeters}
                pathOptions={{
                    color: '#2196F3',
                    weight: 3,
                    fillColor: '#2196F3',
                    fillOpacity: 0.15,
                    dashArray: '8, 6'
                }}
            />
            <Marker
                position={[center.lat, center.lng]}
                icon={centerIcon}
                draggable={true}
                eventHandlers={{
                    drag: handleCenterDrag,
                    dragend: handleCenterDrag
                }}
            />
            <Marker
                position={[center.lat, radiusHandleLng]}
                icon={radiusIcon}
                draggable={true}
                eventHandlers={{
                    drag: handleRadiusDrag,
                    dragend: handleRadiusDrag
                }}
            />
        </>
    );
}

/**
 * Polygon mode: Click to add vertices, render polygon preview
 */
function PolygonSelector({ bounds, onBoundsChange }) {
    const coordinates = bounds.coordinates || [];

    // Click handler to add vertices
    useMapEvents({
        click(e) {
            const { lat, lng } = e.latlng;
            const newCoords = [...coordinates, [lat, lng]];
            onBoundsChange({ type: 'polygon', coordinates: newCoords });
        }
    });

    const positions = coordinates.map(([lat, lng]) => [lat, lng]);

    return (
        <>
            {/* Show polygon fill when 3+ points */}
            {positions.length >= 3 && (
                <Polygon
                    positions={positions}
                    pathOptions={{
                        color: '#2196F3',
                        weight: 3,
                        fillColor: '#2196F3',
                        fillOpacity: 0.08,
                        dashArray: '8, 6'
                    }}
                />
            )}

            {/* Show polyline connecting points when <3 */}
            {positions.length >= 2 && positions.length < 3 && (
                <Polyline
                    positions={positions}
                    pathOptions={{
                        color: '#2196F3',
                        weight: 3,
                        dashArray: '8, 6'
                    }}
                />
            )}

            {/* Vertex markers */}
            {positions.map((pos, i) => (
                <Marker
                    key={`poly-vertex-${i}`}
                    position={pos}
                    icon={vertexIcon}
                    draggable={true}
                    eventHandlers={{
                        dragend: (e) => {
                            const { lat, lng } = e.target.getLatLng();
                            const newCoords = [...coordinates];
                            newCoords[i] = [lat, lng];
                            onBoundsChange({ type: 'polygon', coordinates: newCoords });
                        }
                    }}
                />
            ))}
        </>
    );
}

export { haversineMiles };
export default BoundsSelector;

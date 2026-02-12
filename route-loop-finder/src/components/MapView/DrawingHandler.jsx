import { useEffect, useState, useCallback } from 'react';
import { Polyline, Polygon, CircleMarker, useMap } from 'react-leaflet';

/**
 * Handles drawing mode - allows user to select roads/areas on the map.
 * 
 * Path tool: Click-to-build. Each click adds a shortest-path segment.
 *   - First click sets the start point
 *   - Subsequent clicks add a segment from last point to new point
 *   - Ctrl+click resets the start to the new point (breaks chain)
 *   - Z (undo) moves  the last point back or clears start if at beginning
 * 
 * Lasso tool: Click-and-drag to draw an area selection.
 */
function DrawingHandler({ activeTool, isExcludeMode, onDrawingComplete, onPathPointUndo }) {
    const map = useMap();

    // Lasso state (drag-based)
    const [isDrawing, setIsDrawing] = useState(false);
    const [currentLine, setCurrentLine] = useState([]);

    // Path tool state (click-based)
    const [lastPathPoint, setLastPathPoint] = useState(null);
    const [pathHistory, setPathHistory] = useState([]); // Track all clicked points

    const color = isExcludeMode ? '#c0392b' : '#3068c8';

    // Reset state when tool changes
    useEffect(() => {
        if (activeTool === 'lasso') {
            map.dragging.disable();
            map.getContainer().style.cursor = 'crosshair';
        } else if (activeTool === 'path') {
            // Keep map dragging enabled for path tool so user can pan between clicks
            map.dragging.enable();
            map.getContainer().style.cursor = 'crosshair';
        } else {
            map.dragging.enable();
            map.getContainer().style.cursor = '';
            setIsDrawing(false);
            setCurrentLine([]);
            setLastPathPoint(null);
            setPathHistory([]);
        }
    }, [activeTool, map]);

    // Expose undo handler for path tool
    useEffect(() => {
        const handlePathUndo = () => {
            if (activeTool !== 'path') return false;

            if (pathHistory.length === 0) {
                // No history, do nothing
                return false;
            } else if (pathHistory.length === 1) {
                // Only start point, clear it
                setLastPathPoint(null);
                setPathHistory([]);
                return true; // We handled the undo
            } else {
                // Multiple points, go back to previous
                setPathHistory(prev => prev.slice(0, -1));
                setLastPathPoint(pathHistory[pathHistory.length - 2]);
                return true; // We handled the undo
            }
        };

        if (onPathPointUndo) {
            onPathPointUndo.current = handlePathUndo;
        }
    }, [activeTool, pathHistory, onPathPointUndo]);

    // --- Path tool: click handler ---
    const handlePathClick = useCallback((e) => {
        if (activeTool !== 'path') return;

        const newPoint = e.latlng;
        const isCtrl = e.originalEvent?.ctrlKey || e.originalEvent?.metaKey;

        if (!lastPathPoint || isCtrl) {
            // First click or Ctrl+click: set start point, no segment yet
            setLastPathPoint(newPoint);
            setPathHistory([newPoint]);
        } else {
            // Subsequent click: send segment from lastPathPoint to newPoint
            const coordinates = [
                [lastPathPoint.lat, lastPathPoint.lng],
                [newPoint.lat, newPoint.lng]
            ];
            if (onDrawingComplete) {
                onDrawingComplete(coordinates, 'path', isExcludeMode);
            }
            setLastPathPoint(newPoint);
            setPathHistory(prev => [...prev, newPoint]);
        }
    }, [activeTool, lastPathPoint, isExcludeMode, onDrawingComplete]);

    // --- Lasso tool: drag handlers ---
    const handleMouseDown = useCallback((e) => {
        if (activeTool !== 'lasso') return;
        setIsDrawing(true);
        setCurrentLine([e.latlng]);
    }, [activeTool]);

    const handleMouseMove = useCallback((e) => {
        if (!isDrawing || activeTool !== 'lasso') return;
        setCurrentLine(prev => [...prev, e.latlng]);
    }, [isDrawing, activeTool]);

    const handleMouseUp = useCallback(() => {
        if (!isDrawing || activeTool !== 'lasso') return;
        setIsDrawing(false);

        if (currentLine.length > 1 && onDrawingComplete) {
            const coordinates = currentLine.map(latlng => [latlng.lat, latlng.lng]);
            onDrawingComplete(coordinates, 'lasso', isExcludeMode);
        }

        setCurrentLine([]);
    }, [isDrawing, activeTool, isExcludeMode, currentLine, onDrawingComplete]);

    // Register event handlers
    useEffect(() => {
        if (!activeTool) return;

        if (activeTool === 'path') {
            map.on('click', handlePathClick);
        } else {
            map.on('mousedown', handleMouseDown);
            map.on('mousemove', handleMouseMove);
            map.on('mouseup', handleMouseUp);
        }

        return () => {
            map.off('click', handlePathClick);
            map.off('mousedown', handleMouseDown);
            map.off('mousemove', handleMouseMove);
            map.off('mouseup', handleMouseUp);
        };
    }, [map, activeTool, handlePathClick, handleMouseDown, handleMouseMove, handleMouseUp]);

    if (!activeTool) return null;

    const pathOptions = {
        color: color,
        weight: 4,
        opacity: 0.8,
        dashArray: '10, 10'
    };

    return (
        <>
            {/* Path tool: show marker at last clicked point */}
            {activeTool === 'path' && lastPathPoint && (
                <CircleMarker
                    center={lastPathPoint}
                    radius={6}
                    pathOptions={{
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.8,
                        weight: 2
                    }}
                />
            )}

            {/* Lasso tool: show shape being drawn */}
            {activeTool === 'lasso' && currentLine.length >= 2 && (
                <Polygon positions={currentLine} pathOptions={pathOptions} />
            )}
        </>
    );
}

export default DrawingHandler;

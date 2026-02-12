import { useEffect, useCallback, useState, useRef } from 'react';
import './App.css';

import { MapView } from './components/MapView';
import { ControlPanel } from './components/ControlPanel';
import ElevationProfileWindow from './components/ElevationProfileWindow';
import { useWebSocket } from './hooks/useWebSocket';
import { usePathSets } from './hooks/usePathSets';
import { useAppMode } from './hooks/useAppMode';

function App() {
  // Initialize hooks
  const { status: wsStatus, sendMessage, subscribe } = useWebSocket();
  const {
    pathSetMarkers,
    activePathSetId,
    activePathSet,
    currentPath,
    currentPathIndex,
    filteredPaths,
    distanceRange,
    difficultyRange,
    sortBy,
    sortAscending,
    drawnSelections,
    createPathSet,
    addPathToSet,
    completePathSet,
    selectPathSet,
    addDrawnSelection,
    setDistanceRange,
    setDifficultyRange,
    setSortBy,
    setSortAscending,
    nextPath,
    prevPath,
    undoLastSelection
  } = usePathSets();

  const {
    mode,
    setMode,
    pendingMarker,
    setMarkerPosition,
    clearPendingMarker
  } = useAppMode();

  // Local state for tools
  const [activeTool, setActiveTool] = useState(null); // 'path', 'lasso', or null
  const [isExcludeMode, setIsExcludeMode] = useState(false);
  const [showElevationWindow, setShowElevationWindow] = useState(false);

  // Graph management state
  const [graphs, setGraphs] = useState([]);
  const [activeGraph, setActiveGraph] = useState(null);
  const [graphBounds, setGraphBounds] = useState(null);
  const [isCreatingGraph, setIsCreatingGraph] = useState(false);
  const [graphCreateMode, setGraphCreateMode] = useState('box'); // 'box' or 'polygon'
  const [graphBoundaries, setGraphBoundaries] = useState({});

  // Ref for path tool undo handler
  const pathUndoRef = useRef(null);

  // Queue to track pending requests context (to know if response is include/exclude)
  const pendingRequests = useRef([]);

  // Handle WebSocket messages
  useEffect(() => {
    const unsubscribe = subscribe((message) => {
      console.log('[App] Received message:', message);

      switch (message.type) {
        case 'PATHSET_CREATED':
          createPathSet(message.pathSetId, message.markerPosition);
          setMode('display');
          break;

        case 'PATH_RECEIVED':
          addPathToSet(message.pathSetId, message.path);
          break;

        case 'GENERATION_COMPLETE':
          completePathSet(message.pathSetId);
          break;

        case 'NODES_IN_REGION':
        case 'NODES_ALONG_PATH': {
          // Pop context to see if it was include or exclude
          const context = pendingRequests.current.shift();
          const type = context?.type || 'include'; // default to include if lost

          // For path tool: use server-returned edge geometry if available
          // For lasso tool: construct geometry from user-drawn coordinates
          let selectionFeature;
          if (message.edges && context?.tool === 'path') {
            // Use the actual matched edge geometry from the server
            selectionFeature = {
              ...message.edges,
              properties: {
                ...message.edges.properties,
                mask: message.mask,
                type: type,
                tool: 'path'
              }
            };
          } else {
            // Construct GeoJSON geometry from user-drawn coordinates
            let geometry = null;
            if (context?.coordinates) {
              const coords = context.coordinates.map(([lat, lng]) => [lng, lat]);

              if (context.tool === 'lasso') {
                if (coords.length > 0) {
                  const first = coords[0];
                  const last = coords[coords.length - 1];
                  if (first[0] !== last[0] || first[1] !== last[1]) {
                    coords.push(first);
                  }
                }
                geometry = { type: 'Polygon', coordinates: [coords] };
              } else {
                geometry = { type: 'LineString', coordinates: coords };
              }
            }
            selectionFeature = {
              type: "Feature",
              geometry: geometry,
              properties: {
                mask: message.mask,
                type: type,
                tool: context?.tool
              }
            };
          }

          console.log('[App] Received nodes in region:', message.mask, type);
          addDrawnSelection(selectionFeature);
          break;
        }

        // Graph management messages
        case 'GRAPHS_LIST':
          setGraphs(message.graphs || []);
          if (message.active) {
            setActiveGraph(message.active);
          }
          if (message.boundaries) {
            setGraphBoundaries(message.boundaries);
          }
          break;

        case 'GRAPH_SWITCHED':
          setActiveGraph(message.name);
          break;

        case 'GRAPH_CREATING':
          setIsCreatingGraph(true);
          break;

        case 'GRAPH_CREATED':
          setIsCreatingGraph(false);
          setActiveGraph(message.name);
          setGraphBounds(null);
          setMode('input');
          break;

        case 'GRAPH_CREATE_ERROR':
          setIsCreatingGraph(false);
          console.error('[App] Graph creation error:', message.error);
          alert(`Graph creation failed: ${message.error}`);
          break;

        default:
          console.log('[App] Unknown message type:', message.type);
      }
    });

    return unsubscribe;
  }, [subscribe, createPathSet, addPathToSet, completePathSet, addDrawnSelection, setMode]);

  // Handle map click (in input mode)
  const handleMapClick = useCallback((position) => {
    setMarkerPosition(position);
  }, [setMarkerPosition]);

  // Handle marker click to select a path set
  const handleMarkerClick = useCallback((pathSetId) => {
    selectPathSet(pathSetId);
    setMode('display');
  }, [selectPathSet, setMode]);

  // Handle drawing complete
  const handleDrawingComplete = useCallback((coordinates, tool, exclude) => {
    const context = { type: exclude ? 'exclude' : 'include', coordinates, tool };
    pendingRequests.current.push(context);

    if (tool === 'path') {
      sendMessage('GET_NODES_NEAR_POLYLINE', { coordinates });
    } else if (tool === 'lasso') {
      sendMessage('GET_NODES_IN_REGION', { coordinates });
      setActiveTool(null);
    }
  }, [sendMessage, setActiveTool]);

  // Graph management handlers
  const handleSwitchGraph = useCallback((name) => {
    sendMessage('SWITCH_GRAPH', { name });
  }, [sendMessage]);

  const handleStartGraphCreate = useCallback(() => {
    setGraphBounds(null); // Will be auto-initialized by BoundsSelector
    setGraphCreateMode('box');
    setMode('graphCreate');
  }, [setMode]);

  const handleGraphBoundsChange = useCallback((bounds) => {
    setGraphBounds(bounds);
  }, []);

  // Generator Settings State
  const [genSettings, setGenSettings] = useState(() => {
    const saved = localStorage.getItem('generatorSettings');
    return saved ? JSON.parse(saved) : {
      min_path_len: 15,
      max_path_len: 40,
      loop_ratio: 0.5,
      sim_ceiling: 0.7,
      num_paths: 30,
      algorithm: 'scenic', // 'scenic' or 'direct'
      deduplication: 'centroid', // 'centroid' or 'jaccard'
      min_dist_m: 50 // Centroid distance threshold in meters
    };
  });

  // Save settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('generatorSettings', JSON.stringify(genSettings));
  }, [genSettings]);

  // Handle Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Input Mode: Enter to start generation
      if (e.key === 'Enter' && mode === 'input' && pendingMarker) {
        sendMessage('START_GENERATION', {
          lat: pendingMarker.lat,
          lng: pendingMarker.lng,
          ...genSettings
        });

        localStorage.setItem('lastMapPosition', JSON.stringify({
          center: [pendingMarker.lat, pendingMarker.lng],
          zoom: 13
        }));
      }

      // Graph Create Mode: Enter to create graph
      if (e.key === 'Enter' && mode === 'graphCreate' && graphBounds && !isCreatingGraph) {
        // Validate polygon has enough points
        if (graphBounds.type === 'polygon' && (!graphBounds.coordinates || graphBounds.coordinates.length < 3)) {
          return;
        }
        const name = window.prompt('Enter a name for the new graph:');
        if (name && name.trim()) {
          if (graphBounds.type === 'polygon') {
            sendMessage('CREATE_GRAPH', {
              name: name.trim(),
              boundary_type: 'polygon',
              coordinates: graphBounds.coordinates
            });
          } else if (graphBounds.type === 'circle') {
            sendMessage('CREATE_GRAPH', {
              name: name.trim(),
              boundary_type: 'circle',
              center_lat: graphBounds.center.lat,
              center_lng: graphBounds.center.lng,
              radius_miles: graphBounds.radiusMiles
            });
          } else {
            const { nw, se } = graphBounds;
            sendMessage('CREATE_GRAPH', {
              name: name.trim(),
              boundary_type: 'box',
              north: nw.lat,
              west: nw.lng,
              south: se.lat,
              east: se.lng
            });
          }
        }
      }

      // Graph Create Mode: Escape or Backspace to cancel
      if ((e.key === 'Escape' || e.key === 'Backspace') && mode === 'graphCreate') {
        setGraphBounds(null);
        setMode('input');
      }

      // Display Mode Shortcuts
      if (mode === 'display') {
        // Backspace: Return to Input Mode
        if (e.key === 'Backspace') {
          console.log('Backspace pressed, returning to input mode');
          selectPathSet(null);
          setMode('input');
          setActiveTool(null);
        }

        // Arrow keys: page through paths
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          e.preventDefault();
          nextPath();
        }
        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          e.preventDefault();
          prevPath();
        }

        // 'e' key: Toggle elevation window
        if (e.key === 'e' || e.key === 'E') {
          setShowElevationWindow(prev => !prev);
        }

        // p: path tool
        if (e.key === 'p' || e.key === 'P') {
          setActiveTool(activeTool === 'path' ? null : 'path');
        }

        // l: lasso tool
        if (e.key === 'l' || e.key === 'L') {
          setActiveTool(activeTool === 'lasso' ? null : 'lasso');
        }

        // k: pan / no tool
        if (e.key === 'k' || e.key === 'K') {
          setActiveTool(null);
        }

        // z: Undo last selection (or path point if in path tool)
        if (e.key === 'z' || e.key === 'Z') {
          // First try path tool undo (moves point back)
          const pathHandledUndo = pathUndoRef.current?.();
          if (!pathHandledUndo) {
            // If path tool didn't handle it, do selection undo
            undoLastSelection();
          } else {
            // Path tool moved the point back, also remove the last selection
            undoLastSelection();
          }
        }

        // d: Hold for Exclude mode
        if (e.key === 'd' || e.key === 'D') {
          if (!e.repeat) setIsExcludeMode(true);
        }
      }
    };

    const handleKeyUp = (e) => {
      if (e.key === 'd' || e.key === 'D') {
        setIsExcludeMode(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [mode, pendingMarker, sendMessage, clearPendingMarker, selectPathSet, setMode, undoLastSelection, genSettings, graphBounds, isCreatingGraph, nextPath, prevPath, activeTool, setActiveTool, setIsExcludeMode, setShowElevationWindow, pathUndoRef, graphCreateMode]);

  // Auto-show elevation window when path with elevation data is selected
  useEffect(() => {
    if (currentPath?.properties?.elevation_profile?.length > 1) {
      setShowElevationWindow(true);
    } else {
      setShowElevationWindow(false);
    }
  }, [currentPath]);

  // Reset graph bounds when switching between box/polygon mode
  useEffect(() => {
    if (mode === 'graphCreate') {
      setGraphBounds(null);
    }
  }, [graphCreateMode, mode]);

  return (
    <div className="app">
      <MapView
        mode={mode}
        activeTool={activeTool}
        isExcludeMode={isExcludeMode}
        wsStatus={wsStatus}
        pendingMarker={pendingMarker}
        pathSetMarkers={pathSetMarkers}
        activePathSetId={activePathSetId}
        currentPath={currentPath}
        filteredPaths={filteredPaths}
        drawnSelections={drawnSelections}
        onMapClick={handleMapClick}
        onMarkerClick={handleMarkerClick}
        onDrawingComplete={handleDrawingComplete}
        graphBounds={graphBounds}
        onGraphBoundsChange={handleGraphBoundsChange}
        graphCreateMode={graphCreateMode}
        graphBoundaries={graphBoundaries}
        activeGraph={activeGraph}
        pathUndoRef={pathUndoRef}
      />

      <ControlPanel
        mode={mode}
        setMode={setMode}
        currentPath={currentPath}
        currentPathIndex={currentPathIndex}
        filteredPathsCount={filteredPaths.length}
        totalPathsCount={activePathSet?.paths?.length || 0}
        distanceRange={distanceRange}
        setDistanceRange={setDistanceRange}
        difficultyRange={difficultyRange}
        setDifficultyRange={setDifficultyRange}
        sortBy={sortBy}
        setSortBy={setSortBy}
        sortAscending={sortAscending}
        setSortAscending={setSortAscending}
        onNextPath={nextPath}
        onPrevPath={prevPath}
        hasActivePathSet={!!activePathSetId}
        activeTool={activeTool}
        setActiveTool={setActiveTool}
        isExcludeMode={isExcludeMode}
        setIsExcludeMode={setIsExcludeMode}
        onUndo={undoLastSelection}
        genSettings={genSettings}
        setGenSettings={setGenSettings}
        graphs={graphs}
        activeGraph={activeGraph}
        onSwitchGraph={handleSwitchGraph}
        onStartGraphCreate={handleStartGraphCreate}
        isCreatingGraph={isCreatingGraph}
        graphCreateMode={graphCreateMode}
        setGraphCreateMode={setGraphCreateMode}
        graphBounds={graphBounds}
      />

      {showElevationWindow && currentPath?.properties?.elevation_profile?.length > 1 && (
        <ElevationProfileWindow
          elevationProfile={currentPath.properties.elevation_profile}
          onClose={() => setShowElevationWindow(false)}
        />
      )}
    </div>
  );
}

export default App;

import { useState, useCallback, useMemo, useEffect } from 'react';
import { filterByDistance, filterByDifficulty, filterBySelection, sortPaths } from '../utils/pathFiltering';

/**
 * Manages all path set state - the core data store for the application.
 * A PathSet represents a starting point and all generated routes from it.
 */
export function usePathSets() {
    // Map of pathSetId -> { markerPosition, paths: [] }
    const [pathSets, setPathSets] = useState({});
    const [activePathSetId, setActivePathSetId] = useState(null);
    const [currentPathIndex, setCurrentPathIndex] = useState(0);
    const [distanceRange, setDistanceRange] = useState(() => {
        const saved = localStorage.getItem('distanceRange');
        return saved ? JSON.parse(saved) : [0, 200];
    });
    const [difficultyRange, setDifficultyRange] = useState(() => {
        const saved = localStorage.getItem('difficultyRange');
        return saved ? JSON.parse(saved) : [1, 10];
    });
    const [sortBy, setSortBy] = useState(() => {
        return localStorage.getItem('sortBy') || 'total_miles';
    });
    const [sortAscending, setSortAscending] = useState(true);

    // Save distanceRange to localStorage
    useEffect(() => {
        localStorage.setItem('distanceRange', JSON.stringify(distanceRange));
    }, [distanceRange]);

    // Save difficultyRange to localStorage
    useEffect(() => {
        localStorage.setItem('difficultyRange', JSON.stringify(difficultyRange));
    }, [difficultyRange]);

    // Save sortBy to localStorage
    useEffect(() => {
        localStorage.setItem('sortBy', sortBy);
    }, [sortBy]);


    // drawnSelections: Array of { id, mask, type: 'include'|'exclude', geometry }
    const [drawnSelections, setDrawnSelections] = useState([]);

    // Create a new path set when generation starts
    const createPathSet = useCallback((pathSetId, markerPosition) => {
        setPathSets(prev => ({
            ...prev,
            [pathSetId]: {
                markerPosition,
                paths: [],
                isComplete: false
            }
        }));
        setActivePathSetId(pathSetId);
        setCurrentPathIndex(0);
    }, []);

    // Add a path to an existing path set
    const addPathToSet = useCallback((pathSetId, pathData) => {
        setPathSets(prev => {
            const pathSet = prev[pathSetId];
            if (!pathSet) return prev;

            return {
                ...prev,
                [pathSetId]: {
                    ...pathSet,
                    paths: [...pathSet.paths, pathData]
                }
            };
        });
    }, []);

    // Mark a path set as complete
    const completePathSet = useCallback((pathSetId) => {
        setPathSets(prev => {
            const pathSet = prev[pathSetId];
            if (!pathSet) return prev;

            return {
                ...prev,
                [pathSetId]: { ...pathSet, isComplete: true }
            };
        });
    }, []);

    // Select a path set to display
    const selectPathSet = useCallback((pathSetId) => {
        if (!pathSetId) {
            setActivePathSetId(null);
            return;
        }
        if (pathSets[pathSetId]) {
            setActivePathSetId(pathSetId);
            setCurrentPathIndex(0);
        }
    }, [pathSets]);

    // Add a drawn selection for filtering
    const addDrawnSelection = useCallback((selectionData) => {
        setDrawnSelections(prev => [...prev, selectionData]);
    }, []);

    // Clear drawn selections
    const clearDrawnSelections = useCallback(() => {
        setDrawnSelections([]);
    }, []);

    const undoLastSelection = useCallback(() => {
        setDrawnSelections(prev => {
            if (prev.length === 0) return prev;
            return prev.slice(0, -1);
        });
    }, []);

    // Get the active path set
    const activePathSet = useMemo(() => {
        return activePathSetId ? pathSets[activePathSetId] : null;
    }, [pathSets, activePathSetId]);

    // Get filtered paths based on distance and drawn selections
    const filteredPaths = useMemo(() => {
        if (!activePathSet?.paths?.length) return [];

        let paths = activePathSet.paths;

        // Filter by distance
        paths = filterByDistance(paths, distanceRange[0], distanceRange[1]);

        // Filter by difficulty
        paths = filterByDifficulty(paths, difficultyRange[0], difficultyRange[1]);

        // Filter by drawn selection masks if any
        if (drawnSelections.length > 0) {
            // Aggregate masks
            let strictIncludeMasks = []; // For 'path' tool (ALL nodes)
            let looseIncludeMasks = [];  // For 'lasso' tool (ANY node)
            let excludeMask = BigInt(0); // Single BigInt for OR logic

            drawnSelections.forEach(selection => {
                // Handle both old structure (backward compatibility) and new GeoJSON structure
                const props = selection.properties || selection;
                const mask = BigInt(props.mask || '0');
                const tool = props.tool || 'lasso'; // Default to lasso if undefined (backward compat)

                if (props.type === 'exclude') {
                    excludeMask = excludeMask | mask;
                } else {
                    // Add to appropriate inclusion list
                    if (mask > BigInt(0)) {
                        if (tool === 'path') {
                            strictIncludeMasks.push(mask);
                        } else {
                            looseIncludeMasks.push(mask);
                        }
                    }
                }
            });

            paths = filterBySelection(paths, strictIncludeMasks, looseIncludeMasks, excludeMask);
        }

        // Sort by selected property
        return sortPaths(paths, sortBy, sortAscending);
    }, [activePathSet, distanceRange, difficultyRange, drawnSelections, sortBy, sortAscending]);

    // Ensure currentPathIndex stays within bounds when filteredPaths changes
    useEffect(() => {
        if (filteredPaths.length > 0 && currentPathIndex >= filteredPaths.length) {
            setCurrentPathIndex(0);
        }
    }, [filteredPaths, currentPathIndex]);

    // Reset to first path when sorting changes
    useEffect(() => {
        setCurrentPathIndex(0);
    }, [sortBy, sortAscending]);

    // Get the currently displayed path
    const currentPath = useMemo(() => {
        return filteredPaths[currentPathIndex] || null;
    }, [filteredPaths, currentPathIndex]);

    // Navigation helpers
    const nextPath = useCallback(() => {
        if (currentPathIndex < filteredPaths.length - 1) {
            setCurrentPathIndex(prev => prev + 1);
        }
    }, [currentPathIndex, filteredPaths.length]);

    const prevPath = useCallback(() => {
        if (currentPathIndex > 0) {
            setCurrentPathIndex(prev => prev - 1);
        }
    }, [currentPathIndex]);

    const goToPath = useCallback((index) => {
        if (index >= 0 && index < filteredPaths.length) {
            setCurrentPathIndex(index);
        }
    }, [filteredPaths.length]);

    // Get all path set markers for display
    const pathSetMarkers = useMemo(() => {
        return Object.entries(pathSets).map(([id, pathSet]) => ({
            id,
            position: pathSet.markerPosition,
            isActive: id === activePathSetId,
            pathCount: pathSet.paths.length
        }));
    }, [pathSets, activePathSetId]);

    return {
        // State
        pathSets,
        activePathSetId,
        activePathSet,
        currentPathIndex,
        currentPath,
        filteredPaths,
        distanceRange,
        difficultyRange,
        sortBy,
        sortAscending,
        drawnSelections,
        pathSetMarkers,

        // Actions
        createPathSet,
        addPathToSet,
        completePathSet,
        selectPathSet,
        addDrawnSelection,
        clearDrawnSelections,
        undoLastSelection,
        setDistanceRange,
        setDifficultyRange,
        setSortBy,
        setSortAscending,
        nextPath,
        prevPath,
        goToPath
    };
}

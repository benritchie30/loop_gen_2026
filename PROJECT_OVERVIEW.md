# Route Loop Finder - Project Overview

## 1. High-Level Summary
This application is a **Route Loop Finder** designed to generate circular routes (loops) for activities like cycling or running. Users pick a starting location on a map, specify parameters (distance, difficulty), and the system generates varied loop options using OpenStreetMap (OSM) data.

## 2. System Architecture

The project consists of a **Python Backend** handling heavy graph processing and a **React Frontend** for visualization and interaction, communicating via **WebSockets**.

### Backend (`/backend`)
*   **Framework**: Pure Python `asyncio` + `websockets` (no HTTP web framework like Flask/Django).
*   **Key Files**:
    *   `server.py`: Entry point. Runs the WebSocket server (port 8765), handles client connections, and dispatches messages.
    *   `graph_manager.py`: Singleton that manages:
        *   Loading/saving NetworkX graphs (`.gpickle`) from built-in OSMnx integration.
        *   Spatial queries (nearest node, nodes in polygon).
        *   SRTM Elevation data fetching.
    *   `loop_generator.py`: Contains the core algorithmic logic (`find_paths`) to discover loops on the graph.
*   **Data Storage**:
    *   Graphs are stored as serialized Python objects (`.gpickle`) in `backend/graphs/`.
    *   Metadata (boundaries) are stored as `.boundary.json` sidecar files.

### Frontend (`/route-loop-finder`)
*   **Framework**: React 19 + Vite.
*   **State Management**: Complex local state in `App.jsx` + custom hooks (`usePathSets`, `useWebSocket`).
*   **Map**: `react-leaflet` (Leaflet).
*   **Key Components**:
    *   `MapView.jsx`: Handles map rendering, drawing tools (lasso/path), and markers.
    *   `ControlPanel.jsx`: UI for setting generation parameters (min/max distance, algorithm) and managing graphs.
    *   `ElevationProfileWindow.jsx`: Displays interactive elevation charts.

## 3. Core Workflows

### A. Graph Creation (The "World")
Before routes can be generated, a "graph" (map network) must exist.
1.  **Frontend**: User enters "Graph Create Mode", draws a Box, Polygon, or Circle.
2.  **Message**: `CREATE_GRAPH` sent to backend with coordinates.
3.  **Backend**: `GraphManager` calls `ox.graph_from_...`, downloads OSM data, cleans it, adds elevation, and saves it to disk.

### B. Route Generation
1.  **Frontend**: User clicks a point on the map.
2.  **Message**: `START_GENERATION` sent with `lat`, `lng`, `min_path_len`, `max_path_len`, etc.
3.  **Backend**:
    *   Finds nearest node to click.
    *   Starts `find_paths` generator.
    *   Streams `PATH_RECEIVED` messages back as valid loops are found.
4.  **Frontend**: Real-time updates of the map with new loops.

### C. Tools & Filtering
*   **Exclusion Zones**: User can draw polygons to "exclude" areas. Backend removes these nodes from the graph.
*   **Interactive Tools**: "Path" tool (clicks along a route) and "Lasso" tool (select region) allow users to select nodes for analysis or manual adjustments.

## 4. Key Data Structures
*   **PathSet**: A collection of generated routes starting from a specific point.
*   **Graph**: A NetworkX MultiDiGraph representing the road network (Nodes = intersections, Edges = roads).

## 5. Development Notes
*   **Running**:
    *   Backend: `python backend/server.py`
    *   Frontend: `npm run dev` (in `route-loop-finder/`)
*   **Dependencies**: `osmnx`, `networkx`, `websockets` (Python); `leaflet`, `lucide-react` (JS).

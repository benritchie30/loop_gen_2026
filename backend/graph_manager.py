import pickle
import os
import json
import math
import osmnx as ox
import networkx as nx
from shapely.geometry import Polygon, Point, LineString, MultiLineString, mapping
import geopandas as gpd
import srtm

class GraphManager:
    _instance = None
    _graph = None
    _active_name = None
    _graphs_dir = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GraphManager, cls).__new__(cls)
        return cls._instance

    def set_graphs_dir(self, graphs_dir: str):
        """Sets the directory containing graph files."""
        self._graphs_dir = graphs_dir

    def load_graph(self, path: str):
        """Loads the graph from a pickle file."""
        print(f"Loading graph from {path}...")
        try:
            with open(path, 'rb') as f:
                self._graph = pickle.load(f)
            # Derive the active name from the filename
            self._active_name = os.path.splitext(os.path.basename(path))[0]
            print(f"Graph loaded successfully: {self._active_name}")

            # Auto-add elevation if missing (migration for old graphs)
            sample_node = next(iter(self._graph.nodes))
            if 'elevation' not in self._graph.nodes[sample_node]:
                print("Graph missing elevation data, adding...")
                self._add_elevation_data(self._graph)
                # Save back with elevation
                with open(path, 'wb') as f:
                    pickle.dump(self._graph, f, pickle.HIGHEST_PROTOCOL)
                print("Elevation data added and graph re-saved.")
        except Exception as e:
            print(f"Error loading graph: {e}")
            raise

    def switch_graph(self, name: str):
        """Switch to a different graph by name (without .gpickle extension)."""
        if self._graphs_dir is None:
            raise ValueError("Graphs directory not set. Call set_graphs_dir() first.")
        path = os.path.join(self._graphs_dir, f"{name}.gpickle")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Graph file not found: {path}")
        self.load_graph(path)

    def get_active_name(self) -> str:
        """Returns the name of the currently loaded graph."""
        return self._active_name

    @staticmethod
    def list_graphs(graphs_dir: str) -> list:
        """Lists available graph names (without extension) in the given directory."""
        if not os.path.isdir(graphs_dir):
            return []
        return sorted([
            os.path.splitext(f)[0]
            for f in os.listdir(graphs_dir)
            if f.endswith('.gpickle')
        ])

    @staticmethod
    def get_graph_boundaries(graphs_dir: str) -> dict:
        """Returns {name: boundary_data} for all graphs that have .boundary.json files."""
        boundaries = {}
        if not os.path.isdir(graphs_dir):
            return boundaries
        for f in os.listdir(graphs_dir):
            if f.endswith('.boundary.json'):
                name = f.replace('.boundary.json', '')
                try:
                    with open(os.path.join(graphs_dir, f), 'r') as fh:
                        boundaries[name] = json.load(fh)
                except Exception:
                    pass
        return boundaries

    def _save_boundary(self, name: str, boundary_data: dict):
        """Saves boundary metadata as a sidecar JSON file."""
        path = os.path.join(self._graphs_dir, f"{name}.boundary.json")
        with open(path, 'w') as f:
            json.dump(boundary_data, f)

    def get_graph(self):
        """Returns the loaded graph instance."""
        if self._graph is None:
            raise ValueError("Graph not loaded. Call load_graph() first.")
        return self._graph

    def get_nearest_node(self, lat: float, lng: float):
        """Finds the nearest node to the given coordinates."""
        G = self.get_graph()
        return ox.nearest_nodes(G, lng, lat)

    def get_nodes_in_polygon(self, coordinates: list) -> list:
        """
        Finds all nodes within a polygon defined by coordinates.
        coordinates: List of [lat, lng] pairs (note: check if your polygon needs [lng, lat])
        Returns a list of node IDs.
        """
        G = self.get_graph()
        
        # Ensure coordinates are in the correct order for Polygon (lng, lat)
        # Frontend sends [lat, lng], so we swap
        poly_coords = [(lng, lat) for lat, lng in coordinates]
        
        polygon = Polygon(poly_coords)
        
        nodes_in_region = []
        
        # Basic implementation: check every node. Optimization: use spatial index if needed.
        # For typical graphs (thousands of nodes), this might be slow.
        # Better: use ox.graph_to_gdfs to get nodes as GeoDataFrame, then sjoin or within.
        
        gdf_nodes = ox.graph_to_gdfs(G, nodes=True, edges=False)
        
        # Create a GeoSeries with the polygon
        poly_gdf = gpd.GeoSeries([polygon], crs=gdf_nodes.crs) # Assumes graph crs matches if not specified, usually lat/lon is 4326

        # Actually, ox graphs usually have crs. 
        # If coordinates are lat/lng, we assume EPSG:4326.
        
        # Check if nodes are within the polygon
        # This is strictly for "drawing" feature which returns a mask of nodes.
        
        # Let's do a simple bounding box check first if we care about perf, 
        # but geopandas `within` is reasonably optimized.
        
        # However, checking every node might be heavy.
        # Let's stick to the simplest correct method first.
        
        # Create geometry for all nodes
        # filtered = gdf_nodes[gdf_nodes.geometry.within(polygon)]
        
        # Actually, let's just use the geometry from the GDF
        mask = gdf_nodes.intersects(polygon)
        filtered_nodes = gdf_nodes[mask]
        

        return filtered_nodes.index.tolist()

    def get_nodes_near_polyline(self, coordinates: list, buffer_meters: float = 300.0) -> list:
        """
        Finds all nodes within a certain distance of a polyline.
        coordinates: List of [lat, lng] pairs
        buffer_meters: Distance in meters to buffer the line (approximate if using varying projection, 
                       but for small areas simple degree conversion or treating as meters if projected is needed.
                       However, osmnx graphs are usually unprojected (lat/lon). 
                       Buffering lat/lon by 'meters' requires projection.)
        """
        G = self.get_graph()
        
        # Swap because frontend sends [lat, lng], shapely wants (lng, lat)
        line_coords = [(lng, lat) for lat, lng in coordinates]
        line = LineString(line_coords)
        
        # Project to UTM for accurate buffering in meters
        # We can use the graph's UTM projection if it has one, or project the geometry.
        # Simple heuristic: 1 degree approx 111km. 20m is approx 0.00018 degrees.
        # Let's use a rough degree approximation for speed/simplicity if we don't want to reproject everything.
        # 20m / 111000m/deg ~= 0.00018
        buffer_degrees = buffer_meters / 111111.0
        
        polygon = line.buffer(buffer_degrees)
        
        gdf_nodes = ox.graph_to_gdfs(G, nodes=True, edges=False)
        
        mask = gdf_nodes.intersects(polygon)
        filtered_nodes = gdf_nodes[mask]
        
        return filtered_nodes.index.tolist()

    def get_edges_near_polyline(self, coordinates: list, buffer_meters: float = 25.0):
        """
        Finds shortest path between two clicked points on the graph.
        Snaps both to nearest nodes, returns path nodes + edge GeoJSON.
        """
        G = self.get_graph()

        if len(coordinates) < 2:
            return [], None

        start_lat, start_lng = coordinates[0]
        end_lat, end_lng = coordinates[-1]

        start_node = ox.nearest_nodes(G, start_lng, start_lat)
        end_node = ox.nearest_nodes(G, end_lng, end_lat)

        if start_node == end_node:
            return [start_node], None

        try:
            path = nx.shortest_path(G, start_node, end_node, weight='length')
        except nx.NetworkXNoPath:
            print(f"No path found between {start_node} and {end_node}")
            return [], None

        # Extract edge geometries along the path
        edge_geometries = []
        for u, v in zip(path[:-1], path[1:]):
            if G.has_edge(u, v):
                data = G[u][v][0] if G.is_multigraph() else G[u][v]
                if 'geometry' in data:
                    edge_geometries.append(data['geometry'])
                else:
                    p1 = (G.nodes[u]['x'], G.nodes[u]['y'])
                    p2 = (G.nodes[v]['x'], G.nodes[v]['y'])
                    edge_geometries.append(LineString([p1, p2]))

        edges_geojson = None
        if edge_geometries:
            multi = MultiLineString(edge_geometries)
            edges_geojson = {
                "type": "Feature",
                "geometry": mapping(multi),
                "properties": {}
            }

        return path, edges_geojson

    def create_node_mask(self, node_ids: list) -> int:
        """Creates a bitmask from a list of node IDs."""
        mask = 0
        for node_id in node_ids:
            mask |= (1 << node_id)
        return mask

    @staticmethod
    def _update_edge_names(G):
        """Cleans up edge names from OSM data."""
        for u, v, data in G.edges(data=True):
            names = []
            if 'ref' in data:
                ref_value = data['ref']
                if ';' in ref_value:
                    names.extend(ref_value.split(';'))
                else:
                    names.append(ref_value)
            if 'name' in data:
                if isinstance(data['name'], str):
                    names.append(data['name'])
                elif isinstance(data['name'], list):
                    names.extend(data['name'])
            if len(names) == 0:
                data['name'] = 'None'
            elif len(names) == 1:
                data['name'] = names[0]
            else:
                data['name'] = names
            if 'ref' in data:
                del data['ref']

    @staticmethod
    def _relabel_graph(G):
        """Relabels graph nodes to sequential integers starting from 0."""
        mapping = {old_id: new_id for new_id, old_id in enumerate(G.nodes)}
        return nx.relabel_nodes(G, mapping)

    def _apply_exclusions(self, G, exclusion_zones):
        """Removes nodes/edges that fall within exclusion polygons."""
        if not exclusion_zones:
            return G

        print(f"Applying {len(exclusion_zones)} exclusion zones...")
        initial_nodes = len(G.nodes)
        
        # Convert exclusion zones (list of list of [lat, lng]) to Shapely Polygons
        polygons = []
        for zone in exclusion_zones:
            # Swap to (lng, lat) for Shapely
            poly_coords = [(lng, lat) for lat, lng in zone]
            if len(poly_coords) >= 3:
                polygons.append(Polygon(poly_coords))
        
        if not polygons:
            return G

        # Identify nodes to remove
        nodes_to_remove = set()
        for node, data in G.nodes(data=True):
            # Check against all polygons
            pt = Point(data['x'], data['y'])
            for poly in polygons:
                if poly.contains(pt):
                    nodes_to_remove.add(node)
                    break
        
        if nodes_to_remove:
            G.remove_nodes_from(nodes_to_remove)
            print(f"Removed {len(nodes_to_remove)} nodes based on exclusion zones.")
            
        # Clean up isolated nodes if any (OSMnx usually handles this but good to be safe)
        # G = ox.utils_graph.remove_isolated_nodes(G)
        
        print(f"Graph filtered: {initial_nodes} -> {len(G.nodes)} nodes.")
        return G

    def generate_graph(self, name: str, south: float, west: float, north: float, east: float,
                       custom_filter: str = '["highway"~"trunk|primary|secondary|tertiary"]',
                       exclusion_zones: list = None):
        """Downloads, processes, and saves a new graph from OSMnx using bounding box."""
        if self._graphs_dir is None:
            raise ValueError("Graphs directory not set.")

        print(f"Generating graph '{name}' for bbox: S={south}, W={west}, N={north}, E={east}")
        G = ox.graph_from_bbox(
            bbox=(north, south, east, west),
            network_type='drive',
            custom_filter=custom_filter
        )

        G = self._apply_exclusions(G, exclusion_zones)
        self._update_edge_names(G)
        G = self._relabel_graph(G)
        self._add_elevation_data(G)


        os.makedirs(self._graphs_dir, exist_ok=True)
        file_path = os.path.join(self._graphs_dir, f"{name}.gpickle")
        with open(file_path, 'wb') as f:
            pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)

        # Save boundary metadata
        self._save_boundary(name, {
            'type': 'box',
            'north': north, 'south': south, 'east': east, 'west': west
        })

        print(f"Graph saved at: {file_path}")
        return name

    def generate_graph_from_polygon(self, name: str, coordinates: list,
                                     custom_filter: str = '["highway"~"trunk|primary|secondary|tertiary"]',
                                     exclusion_zones: list = None):
        """Downloads, processes, and saves a new graph from OSMnx using polygon boundary.
        coordinates: list of [lat, lng] pairs."""
        if self._graphs_dir is None:
            raise ValueError("Graphs directory not set.")

        # Shapely uses (lng, lat) order
        poly = Polygon([(lng, lat) for lat, lng in coordinates])
        print(f"Generating graph '{name}' from polygon with {len(coordinates)} vertices")

        G = ox.graph_from_polygon(
            poly,
            network_type='drive',
            custom_filter=custom_filter
        )

        G = self._apply_exclusions(G, exclusion_zones)
        self._update_edge_names(G)
        G = self._relabel_graph(G)
        self._add_elevation_data(G)

        os.makedirs(self._graphs_dir, exist_ok=True)
        file_path = os.path.join(self._graphs_dir, f"{name}.gpickle")
        with open(file_path, 'wb') as f:
            pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)

        # Save boundary metadata
        self._save_boundary(name, {
            'type': 'polygon',
            'coordinates': coordinates
        })

        print(f"Graph saved at: {file_path}")
        return name

    def generate_graph_from_circle(self, name: str, center_lat: float, center_lng: float,
                                    radius_miles: float,
                                    custom_filter: str = '["highway"~"trunk|primary|secondary|tertiary"]',
                                    exclusion_zones: list = None):
        """Downloads, processes, and saves a new graph from a circular boundary.
        radius_miles: radius in miles."""
        if self._graphs_dir is None:
            raise ValueError("Graphs directory not set.")

        # Convert miles to approximate degrees (1 degree lat ≈ 69 miles)
        radius_deg_lat = radius_miles / 69.0
        radius_deg_lng = radius_miles / (69.0 * abs(math.cos(math.radians(center_lat))))
        
        # Create elliptical polygon to account for lat/lng distortion
        center = Point(center_lng, center_lat)
        # Use affine scaling to make a proper circle in geographic coords
        circle = center.buffer(1, resolution=64)
        from shapely.affinity import scale
        circle = scale(circle, xfact=radius_deg_lng, yfact=radius_deg_lat)

        print(f"Generating graph '{name}' from circle: center=({center_lat}, {center_lng}), radius={radius_miles}mi")

        G = ox.graph_from_polygon(
            circle,
            network_type='drive',
            custom_filter=custom_filter
        )

        G = self._apply_exclusions(G, exclusion_zones)
        self._update_edge_names(G)
        G = self._relabel_graph(G)
        self._add_elevation_data(G)

        os.makedirs(self._graphs_dir, exist_ok=True)
        file_path = os.path.join(self._graphs_dir, f"{name}.gpickle")
        with open(file_path, 'wb') as f:
            pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)

        # Save boundary metadata
        self._save_boundary(name, {
            'type': 'circle',
            'center': [center_lat, center_lng],
            'radius_miles': radius_miles
        })

        print(f"Graph saved at: {file_path}")
        return name

    @staticmethod
    def _add_elevation_data(G):
        """Adds elevation (meters) to each node using SRTM data.
        SRTM tiles are automatically downloaded and cached on first use."""
        print("Adding elevation data from SRTM...")
        elevation_data = srtm.get_data()
        missing = 0
        for node, data in G.nodes(data=True):
            lat = data.get('y', 0)
            lng = data.get('x', 0)
            elev = elevation_data.get_elevation(lat, lng)
            data['elevation'] = elev if elev is not None else 0
            if elev is None:
                missing += 1
        if missing > 0:
            print(f"Warning: {missing} nodes had no SRTM elevation data (set to 0).")
        print(f"Elevation added to {len(G.nodes) - missing}/{len(G.nodes)} nodes.")

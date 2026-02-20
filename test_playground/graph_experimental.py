import osmnx as ox
import networkx as nx
import pickle
import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from collections import Counter
import numpy as np
import heapq
from shapely.geometry import Point, LineString, MultiLineString
import sys
# Add project root to sys.path to allow importing from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.loop_generator import weight_function_turns_dist, PathNode

# Configuration

def get_graph(path):
    if not os.path.exists(path):
        print(f"Graph file not found: {path} - checking absolute path...")
        # Try relative to script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.join(base_dir, path)
        if os.path.exists(abs_path):
             path = abs_path
        else:
             print(f"Graph file not found at {path} or {abs_path}")
             return None
            
    with open(path, 'rb') as f:
        G = pickle.load(f)
        
    print(f"Loaded graph from {path} with {len(G.nodes)} nodes and {len(G.edges)} edges.")
    return G

def download_test_graph_bbox(coords, name, network_type='all', **kwargs):
    """Downloads a graph from a bounding box and saves it. Accepts **kwargs for ox.graph_from_bbox."""
    # User provided coords as (south, west, north, east) tuple in main
    south, west, north, east = coords
    
    # New osmnx expects (left, bottom, right, top) -> (west, south, east, north)
    # Adjusting input to match expected (left, bottom, right, top)
    bbox_tuple = (west, south, east, north)
    
    print(f"Downloading graph '{name}' from bbox {bbox_tuple}...")
    try:
        G = ox.graph_from_bbox(bbox=bbox_tuple, network_type=network_type, **kwargs)
    except Exception as e:
        print(f"Error downloading graph: {e}")
        return None
    
    # Save to test_playground/graphs
    base_dir = os.path.dirname(os.path.abspath(__file__))
    graphs_dir = os.path.join(base_dir, 'graphs')
    os.makedirs(graphs_dir, exist_ok=True)
    
    save_path = os.path.join(graphs_dir, f"{name}.gpickle")
    
    with open(save_path, 'wb') as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    print(f"Graph saved to {save_path}")
    print(f"Graph saved to {save_path}")
    return save_path

def download_test_graph_circle(center_point, dist, name, network_type='all', **kwargs):
    """Downloads a graph from a center point and radius (dist in meters) and saves it."""
    print(f"Downloading graph '{name}' from point {center_point} with radius {dist}m...")
    try:
        G = ox.graph_from_point(center_point, dist=dist, network_type=network_type, **kwargs)
    except Exception as e:
        print(f"Error downloading graph: {e}")
        return None
    
    # Save to test_playground/graphs
    base_dir = os.path.dirname(os.path.abspath(__file__))
    graphs_dir = os.path.join(base_dir, 'graphs')
    os.makedirs(graphs_dir, exist_ok=True)
    
    save_path = os.path.join(graphs_dir, f"{name}.gpickle")
    
    with open(save_path, 'wb') as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    print(f"Graph saved to {save_path}")
    return save_path


def remove_node_and_merge(G, u, n, v):
    # Get Edge Data (u -> n)
    # Handle MultiDiGraph: get_edge_data returns {key: {attrs}}
    edges_u_n = G.get_edge_data(u, n)
    if edges_u_n == None:
        G.remove_node(n)
        return False
    key_u = list(edges_u_n.keys())[0] # Take first edge
    attr_u = edges_u_n[key_u]
    
    # Get Edge Data (n -> v)
    edges_n_v = G.get_edge_data(n, v)
    if edges_n_v == None:
        G.remove_node(n)
        return False
    key_v = list(edges_n_v.keys())[0] # Take first edge
    attr_v = edges_n_v[key_v]

    # 1. Merge Geometry
    geo1 = attr_u.get('geometry')
    geo2 = attr_v.get('geometry')

    # Fallback if geometry missing (straight line from point coords)
    if not geo1:
        p1 = Point(G.nodes[u]['x'], G.nodes[u]['y'])
        p2 = Point(G.nodes[n]['x'], G.nodes[n]['y'])
        geo1 = LineString([p1, p2])
    if not geo2:
        p2 = Point(G.nodes[n]['x'], G.nodes[n]['y'])
        p3 = Point(G.nodes[v]['x'], G.nodes[v]['y'])
        geo2 = LineString([p2, p3])
    # shapely coords are list of tuples (x, y)
    coords1 = list(geo1.coords)
    coords2 = list(geo2.coords)
    start1 = coords1[0]
    end1 = coords1[-1]
    start2 = coords2[0]
    end2 = coords2[-1]
    if start1 == start2:
        coords1 = coords1[::-1]
    elif start1 == end2:
        coords1 = coords1[::-1]
        coords2 = coords2[::-1]
    elif end1 == end2:
        coords2 = coords2[::-1]
    new_coords = coords1[:-1] + coords2
    new_geometry = LineString(new_coords)
    # 2. Merge Attributes
    new_attr = attr_u.copy()
    new_attr['geometry'] = new_geometry
    new_attr['length'] = attr_u.get('length', 0) + attr_v.get('length', 0)
    # 3. Modify Graph
    # Add new edge u->v
    G.remove_node(n)
    G.add_edge(u, v, **new_attr)
    G.add_edge(v, u, **new_attr)
    return True


def remove_dead_ends_v3(G):
    print("in remove_dead_ends_v3")

    G_undir = ox.convert.to_undirected(G)

    dead_end_nodes = [n for n, d in G_undir.degree() if d == 1]
    print(f"Found {len(dead_end_nodes)} dead end nodes")
    potential_intersection_nodes = []
    for dead_end_node in dead_end_nodes:
        next_node = next(G_undir.neighbors(dead_end_node))
        if dead_end_node in G.nodes:
            G.remove_node(dead_end_node)
        if dead_end_node in G_undir.nodes:
            G_undir.remove_node(dead_end_node)
        if G_undir.degree[next_node] == 1:
            dead_end_nodes.append(next_node)
        else:
            potential_intersection_nodes.append(next_node)
    intermediate_nodes = [n for n, d in G_undir.degree() if d == 2 and n in potential_intersection_nodes]



    last = []
    for intermediate_node in intermediate_nodes:
        if intermediate_node not in G.nodes:
            # ox.plot_graph_route(G_undir, [intermediate_node])
            continue
        neigbors = list(G.neighbors(intermediate_node))
        

        if len(neigbors) == 1:
            curr = intermediate_node
            last = None
            while len(neigbors) == 1:
                if last:
                    # ox.plot_graph_route(G, [last])
                    G.remove_node(last)
                neigbors = list(G.neighbors(curr))
                if len(neigbors) != 1:
                    break
                last = curr
                curr = neigbors[0]
            intermediate_nodes.append(curr)
        elif len(neigbors) == 2:

            edges_merged_success = remove_node_and_merge(G, neigbors[0], intermediate_node, neigbors[1])
        else:
            print("outlier")
            ox.plot_graph_route(G, [intermediate_node], route_color='g')
            print(neigbors)
    # dead_end_nodes = [n for n, d in G_undir.degree() if d == 1]
        
    return



      
def remove_self_loops(G):
    """
    Removes edges that connect a node to itself (self-loops).
    """
    print("\n--- Removing Self Loops ---")
    # nx.selfloop_edges returns generator
    edges_to_remove = list(nx.selfloop_edges(G))
    if edges_to_remove:
        G.remove_edges_from(edges_to_remove)
        print(f"Removed {len(edges_to_remove)} self-loop edges.")
    else:
        print("No self-loops found.")

def filter_keep_only_attribute(G, attribute):
    """
    Removes all edges that do NOT have the specified attribute.
    """
    print(f"\n--- Filtering to keep ONLY edges with attribute '{attribute}' ---")
    edges_to_remove = []
    for u, v, k, data in G.edges(keys=True, data=True):
        if attribute not in data:
            edges_to_remove.append((u, v, k))
            
    if edges_to_remove:
        G.remove_edges_from(edges_to_remove)
        print(f"Removed {len(edges_to_remove)} edges that were missing '{attribute}'.")
    else:
        print(f"No edges removed; all had attribute '{attribute}'.")
    
    # User commented out:
    # G = ox.utils_graph.remove_isolated_nodes(G)
    print(f"Graph now has {len(G.nodes)} nodes and {len(G.edges)} edges.")
    return G

def plot_graph_colored_by_attribute(G, attribute):
    """
    Plots the graph with edges colored by the value of a specific attribute.
    Includes an interactive legend: hover over legend items to highlight corresponding edges.
    """
    print(f"\n--- Plotting graph colored by attribute '{attribute}' ---")
    
    # Check if attribute exists in any edge
    has_attr = False
    for u,v,k,d in G.edges(keys=True, data=True):
        if attribute in d:
             has_attr = True
             break
    
    if not has_attr:
         print(f"Attribute '{attribute}' not found in graph edges.")
         return

    # 1. Collect all unique values and counts
    unique_values = set()
    counts = Counter()
    edge_values = []
    
    for u, v, k, data in G.edges(keys=True, data=True):
        val = "MISSING"
        if attribute in data:
            raw_val = data[attribute]
            if isinstance(raw_val, list):
                val = raw_val[0]
            else:
                val = raw_val
        
        val_str = str(val)
        unique_values.add(val_str)
        counts[val_str] += 1
        edge_values.append(val_str)
            
    sorted_values = sorted(list(unique_values))
    
    # 2. Assign colors
    n_colors = len(sorted_values)
    if n_colors <= 20:
        cmap = cm.get_cmap('tab20', n_colors)
    else:
        cmap = cm.get_cmap('nipy_spectral', n_colors)
    
    value_to_color = {}
    print("\nLegend (Color Key):")
    print(f"{'Value':<30} | {'Color':<10} | {'Count':<5}")
    print("-" * 55)
    
    for idx, val in enumerate(sorted_values):
        rgba = cmap(idx) 
        hex_color = mcolors.to_hex(rgba)
        value_to_color[val] = hex_color
        print(f"{val:<30} | {hex_color:<10} | {counts[val]:<5}")
        
    # 3. Create initial edge color list
    edge_colors = [value_to_color.get(val, "#000000") for val in edge_values]
        
    # 4. Plot
    fig, ax = ox.plot_graph(
        G, 
        edge_color=edge_colors, 
        node_size=0, 
        edge_linewidth=1.5, 
        show=False, 
        close=False,
        bgcolor='white',
        edge_alpha=0.8
    )
    
    edge_collection = None
    for collection in ax.collections:
        if len(collection.get_paths()) == len(G.edges):
            edge_collection = collection
            break
            
    if edge_collection is None:
        print("Could not locate edge collection for interactivity.")
        plt.show()
        return

    # 5. Interactive Legend
    legend_lines = []
    for val in sorted_values:
        line = Line2D([0], [0], color=value_to_color[val], lw=4, label=f"{val} ({counts[val]})")
        legend_lines.append(line)
        
    leg = ax.legend(handles=legend_lines, loc='best', fontsize='x-small', title=attribute)

    def on_hover(event):
        if event.inaxes != ax:
            return
            
        highlight_val = None
        for text in leg.get_texts():
            contains, _ = text.contains(event)
            if contains:
                label = text.get_text()
                split_idx = label.rfind(" (")
                if split_idx != -1:
                    highlight_val = label[:split_idx]
                break
        
        if highlight_val is not None:
            new_colors = []
            new_widths = []
            for val, orig_col in zip(edge_values, edge_colors):
                if val == highlight_val:
                    new_colors.append(orig_col)
                    new_widths.append(3.0)
                else:
                    new_colors.append('#eeeeee')
                    new_widths.append(0.5)
            
            edge_collection.set_color(new_colors)
            edge_collection.set_linewidth(new_widths)
            fig.canvas.draw_idle()
        else:
            edge_collection.set_color(edge_colors)
            edge_collection.set_linewidth(1.5)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect('motion_notify_event', on_hover)
    
    plt.title(f"Graph colored by '{attribute}' (Hover over legend text to highlight)")
    plt.tight_layout()
    plt.show()



def keep_shortest_edge(G):
    """
    Simplifies the graph in-place by keeping only the shortest edge
    between any two nodes in a MultiDiGraph.
    """
    print(f"\n--- Keeping only shortest edges (In-Place) ---")
    initial_edge_count = len(G.edges)
    edges_to_remove = []

    for u in G.nodes():
        for v in G[u]:
            if len(G[u][v]) > 1:
                # Found multi-edges between u and v
                min_len = float('inf')
                best_key = None
                
                # Find the shortest edge key
                for k, data in G[u][v].items():
                    length = data.get('length', float('inf'))
                    if length < min_len:
                        min_len = length
                        best_key = k
                
                # Mark all other keys for removal
                for k in G[u][v]:
                    if k != best_key:
                        edges_to_remove.append((u, v, k))

    if edges_to_remove:
        G.remove_edges_from(edges_to_remove)
        print(f"Removed {len(edges_to_remove)} redundant edges.")
    else:
        print("No redundant multi-edges found.")

    print(f"Graph edges reduced from {initial_edge_count} to {len(G.edges)}")
    return G

def get_nodes_with_edge_attribute_values(G, attribute, values):
    """
    Returns a set of nodes that are part of edges with specific attribute values.
    Handles both single values and lists of values (common in OSM data).
    """
    target_nodes = set()
    print(f"\n--- Finding nodes on edges with {attribute} in {values} ahahahah---")
    
    # Ensure values is a set for faster lookup
    value_set = set(values)
    
    for u, v, k, data in G.edges(keys=True, data=True):
        if attribute not in data:
            continue
            
        attr_val = data[attribute]
        # OSMnx can return lists for tags
        match = False
        if isinstance(attr_val, list):
            # Check if any value in the list matches our target values
            if any(val in value_set for val in attr_val):
                match = True
        else:
            if attr_val in value_set:
                match = True
                
        if match:
            target_nodes.add(u)
            target_nodes.add(v)
            
    print(f"Found {len(target_nodes)} nodes associated with {attribute}={values}")
    return target_nodes

def process_graph_old_version(G):

    G = filter_keep_only_attribute(G, 'highway')
    
    # 2. Aggressive Attribute Stripping (User Request)
    # Remove all edge attributes except geometry, length, and name.
    # This allows merging of different road types/names if they maintain geometry/length.
    print("removing attributes from edges")
    whitelist = {'geometry', 'length', 'name', 'osmid'}
    for u, v, k, data in G.edges(keys=True, data=True):
        keys_to_pop = [key for key in list(data.keys()) if key not in whitelist]
        for key in keys_to_pop:
            data.pop(key)
    
    # NEW STEP: Keep only the shortest edge between nodes
    # G = keep_shortest_edge(G)
    
    remove_self_loops(G)
    remove_dead_ends_v3(G)
    # 4. Remove Isolates
    G.remove_nodes_from(list(nx.isolates(G)))

    # 3. Simplify (Merge 2-degree nodes)
    ox.plot_graph(G)
    
    return G




def simplify_graph_topology(G):
    """
    Simplifies the graph's topology by removing all nodes that serve only as 
    intermediaries between two other nodes (undirected degree = 2), and merges 
    their incident edges.
    """
    print("\n--- Simplifying Topology (Merging degree-2 nodes) ---")
    initial_nodes = len(G.nodes)
    
    nodes_removed = 0
    while True:
        # We must recalculate degrees each iteration because merging edges changes topology
        G_undir = G.to_undirected()
        
        # Find all nodes with exactly 2 neighbors in the undirected graph
        degree_2_nodes = [n for n, d in G_undir.degree() if d == 2]
        
        removed_in_this_pass = 0
        for n in degree_2_nodes:
            if n not in G: 
                continue
                
            neighbors = list(G_undir.neighbors(n))
            if len(neighbors) == 2:
                u, v = neighbors[0], neighbors[1]
                
                # Make sure it's not a self-loop situation and both are in the graph
                if u != v and u in G and v in G:
                    # remove_node_and_merge requires the sequence u -> n -> v
                    # Check which way the edges go and pass them in that order
                    if G.has_edge(u, n) and G.has_edge(n, v):
                        success = remove_node_and_merge(G, u, n, v)
                    elif G.has_edge(v, n) and G.has_edge(n, u):
                        success = remove_node_and_merge(G, v, n, u)
                    else:
                        success = False
                        
                    if success:
                        removed_in_this_pass += 1
                        nodes_removed += 1
        
        # If we didn't find any more nodes to merge, we're done
        if removed_in_this_pass == 0:
            break
            
    print(f"Topology simplified: removed {nodes_removed} intermediate nodes.")
    print(f"Graph nodes reduced from {initial_nodes} -> {len(G.nodes)}")
    return G


def process_graph(G):

    G = filter_keep_only_attribute(G, 'highway')
    
    whitelist = {'geometry', 'length', 'name', 'osmid', 'highway'}
    for u, v, k, data in G.edges(keys=True, data=True):
        keys_to_pop = [key for key in list(data.keys()) if key not in whitelist]
        for key in keys_to_pop:
            data.pop(key)
    
    print(f"Before pruning: {len(G.nodes)} nodes, {len(G.edges)} edges")
    
    # 1. Prune dead ends, tiny loops, and keep connectors between large components
    prune_graph_biconnected(G, min_component_length=3000)
    ox.plot_graph(G, node_size=0, edge_linewidth=1, bgcolor='white')

    # 2. Remove redundant multi-edges (keep only the shortest edge between intersection pairs)
    keep_shortest_edge(G)
    # ox.plot_graph(G, node_size=0, edge_linewidth=1, bgcolor='white', title="After Shortest Edge")
    
    # 3. Simplify topology (remove degree-2 non-intersection nodes)
    simplify_graph_topology(G)
    ox.plot_graph(G, node_size=15, edge_linewidth=1, bgcolor='white')

    print(f"Final simplified graph: {len(G.nodes)} nodes, {len(G.edges)} edges")
    
    return G


def print_unique_edge_attributes(G):
    """Prints all unique attribute keys found in the graph edges."""
    print("\n--- Unique Edge Attributes ---")
    unique_keys = set()
    for u, v, k, data in G.edges(keys=True, data=True):
        unique_keys.update(data.keys())
    
    sorted_keys = sorted(list(unique_keys))
    print(f"Found {len(sorted_keys)} unique attributes: {sorted_keys}")
    
    # Optional: Print a few examples if useful
    # for key in sorted_keys:
    #     print(f"  {key}")

def demo_biconnected_components(G, start_node):
    """
    Visualizes biconnected components on the graph.
    
    A biconnected component is a maximal subgraph where removing ANY single node
    still leaves the rest connected. This means every pair of nodes in the 
    component lies on at least one simple cycle (loop) together.
    
    Why this solves the pruning problem:
    - Dead-end roads form "bridges" — edges whose removal disconnects the graph.
      Nodes only reachable through bridges can never be part of a loop.
    - Biconnected components are exactly the parts of the graph between bridges.
    - Any node in a biconnected component with 3+ nodes can participate in a loop.
    - Tree-like branches (no matter how complex) are automatically excluded.
    
    Color coding in the plot:
    - Each biconnected component with 3+ nodes gets its own color
    - RED nodes = not part of any loopable component (dead ends, bridges, trees)
    - GREEN star = start node
    """
    print("\n=== Biconnected Components Demo ===")
    
    # Convert to undirected for analysis
    G_undir = G.to_undirected()
    
    # Get biconnected components (each is a set of nodes)
    components = list(nx.biconnected_components(G_undir))
    
    # Filter to components with 3+ nodes (need at least 3 for a real loop)
    loop_components = [c for c in components if len(c) >= 3]
    bridge_components = [c for c in components if len(c) < 3]
    
    print(f"Total biconnected components: {len(components)}")
    print(f"  Components with loops (3+ nodes): {len(loop_components)}")
    print(f"  Bridge/dead-end components (<3 nodes): {len(bridge_components)}")
    
    # All valid nodes (union of all loop components)
    valid_nodes = set()
    for c in loop_components:
        valid_nodes.update(c)
    
    invalid_nodes = set(G.nodes()) - valid_nodes
    
    print(f"\nValid nodes (can participate in loops): {len(valid_nodes)}")
    print(f"Invalid nodes (dead ends/bridges): {len(invalid_nodes)}")
    print(f"Start node {start_node} is {'VALID' if start_node in valid_nodes else 'INVALID'}")
    
    # Sort components by size for display
    loop_components.sort(key=len, reverse=True)
    for i, c in enumerate(loop_components[:10]):  # Show top 10
        contains_start = "★ CONTAINS START" if start_node in c else ""
        print(f"  Component {i}: {len(c)} nodes {contains_start}")
    
    # --- Visualization ---
    # Assign colors per component
    n_comps = len(loop_components)
    if n_comps > 0:
        cmap_func = cm.get_cmap('tab20', max(n_comps, 1))
    
    node_to_color = {}
    for idx, comp in enumerate(loop_components):
        color = mcolors.to_hex(cmap_func(idx % 20))
        for node in comp:
            node_to_color[node] = color
    
    # Node colors: component color for valid, red for invalid
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        if node == start_node:
            node_colors.append('#00ff00')  # Green for start
            node_sizes.append(80)
        elif node in node_to_color:
            node_colors.append(node_to_color[node])
            node_sizes.append(15)
        else:
            node_colors.append('#ff0000')  # Red for invalid
            node_sizes.append(25)
    
    # Edge colors: color if both endpoints valid, gray otherwise
    edge_colors = []
    for u, v, k in G.edges(keys=True):
        if u in valid_nodes and v in valid_nodes:
            # Use the color of u's component
            edge_colors.append(node_to_color.get(u, '#888888'))
        else:
            edge_colors.append('#dddddd')  # Light gray for dead-end edges
    
    fig, ax = ox.plot_graph(
        G,
        node_color=node_colors,
        node_size=node_sizes,
        edge_color=edge_colors,
        edge_linewidth=1.5,
        bgcolor='white',
        show=False,
        close=False
    )
    
    plt.suptitle(f"Biconnected Components\n"
                f"{len(valid_nodes)} valid nodes (colored) | "
                f"{len(invalid_nodes)} invalid nodes (red)", fontsize=10)
    plt.show()


def prune_graph_biconnected(G, min_component_length=500):
    """
    Prunes the graph by removing dead-end branches and tiny loop components.
    
    Uses the "block-cut tree" to decide what to keep:
    - Biconnected components (blocks) with total edge length >= min_component_length are "large"
    - Bridge paths between large blocks are kept (connectors)
    - Small blocks that sit between two large blocks are kept (connectors)
    - Dead-end branches and isolated tiny loops are removed
    
    Args:
        G: NetworkX MultiDiGraph (modified in place)
        min_component_length: Minimum total edge length (meters) for a component to be kept.
                              Components below this are removed unless they connect two larger ones.
    
    Returns:
        G: The pruned graph (same object, modified in place)
    """
    print(f"\n=== Pruning Graph (min_component_length={min_component_length}m) ===")
    initial_nodes = len(G.nodes)
    initial_edges = len(G.edges)
    
    # 1. Convert to undirected for biconnected component analysis
    G_undir = G.to_undirected()
    
    # 2. Find biconnected components (each is a frozenset of nodes)
    components = list(nx.biconnected_components(G_undir))
    print(f"Found {len(components)} biconnected components")
    
    # 3. Measure each component by total edge length
    comp_lengths = []
    for comp in components:
        comp_set = set(comp)
        total_length = 0
        seen_edges = set()
        for u in comp_set:
            for v in G_undir.neighbors(u):
                if v in comp_set:
                    edge_pair = (min(u, v), max(u, v))
                    if edge_pair not in seen_edges:
                        seen_edges.add(edge_pair)
                        # MultiGraph: G_undir[u][v] = {key: {attrs}, ...}
                        edge_dict = G_undir[u][v]
                        min_length = min(
                            d.get('length', 0) for d in edge_dict.values()
                        ) if edge_dict else 0
                        total_length += min_length
        comp_lengths.append(total_length)
    
    # 4. Build the block-cut tree
    #    Nodes: blocks (biconnected components) and cut vertices (articulation points)
    #    Edges: a cut vertex connects to each block it belongs to
    art_points = set(nx.articulation_points(G_undir))
    
    block_cut_tree = nx.Graph()
    for i, comp in enumerate(components):
        block_id = f"B{i}"
        # KEY: A component needs >= 3 nodes to contain a cycle.
        # 2-node components are ALWAYS bridge edges (dead ends or connectors)
        # and can never form loops, no matter how long the edge is.
        is_large = len(comp) >= 3 and comp_lengths[i] >= min_component_length
        block_cut_tree.add_node(block_id, type='block', index=i,
                                length=comp_lengths[i], is_large=is_large,
                                node_count=len(comp))
        for ap in art_points:
            if ap in comp:
                block_cut_tree.add_edge(block_id, ap)
                block_cut_tree.nodes[ap]['type'] = 'cut_vertex'
    
    # 5. Find the minimal subtree spanning all large blocks
    #    Iterative DFS: marks subtrees that contain at least one large block
    large_blocks = [n for n in block_cut_tree.nodes()
                    if block_cut_tree.nodes[n].get('is_large')]
    
    print(f"Large components (>= 3 nodes AND >= {min_component_length}m): {len(large_blocks)}")
    for b in large_blocks:
        idx = block_cut_tree.nodes[b]['index']
        print(f"  {b}: {len(components[idx])} nodes, {comp_lengths[idx]:.0f}m total edge length")
    
    if not large_blocks:
        print("WARNING: No components meet the minimum length. Graph would be empty.")
        print("Consider lowering min_component_length.")
        return G
    
    large_set = set(large_blocks)
    
    # Iterative post-order DFS to mark needed subtrees
    # (avoids Python recursion limit on large graphs)
    def mark_needed_iterative(root):
        """Iterative DFS: marks nodes on paths between large blocks."""
        # First pass: build parent map via BFS
        parent = {root: None}
        order = []  # visit order for post-order processing
        stack = [root]
        while stack:
            node = stack.pop()
            order.append(node)
            for neighbor in block_cut_tree.neighbors(node):
                if neighbor not in parent:
                    parent[neighbor] = node
                    stack.append(neighbor)
        
        # Second pass: post-order (reverse of visit order)
        needed = {}
        for node in reversed(order):
            needed[node] = node in large_set
            for neighbor in block_cut_tree.neighbors(node):
                if parent.get(neighbor) == node:  # neighbor is child
                    if needed.get(neighbor, False):
                        needed[node] = True
            if needed[node]:
                block_cut_tree.nodes[node]['keep'] = True
    
    # Handle disconnected block-cut tree (graph may have multiple components)
    visited_bct = set()
    for lb in large_blocks:
        if lb not in visited_bct:
            # BFS to find all nodes in this tree component
            tree_component = set(nx.node_connected_component(block_cut_tree, lb))
            visited_bct.update(tree_component)
            mark_needed_iterative(lb)
    
    # 6. Collect valid nodes from kept blocks and cut vertices
    valid_nodes = set()
    kept_blocks = 0
    pruned_blocks = 0
    for node in block_cut_tree.nodes():
        node_data = block_cut_tree.nodes[node]
        if node_data.get('keep'):
            if node_data.get('type') == 'block':
                idx = node_data['index']
                valid_nodes.update(components[idx])
                kept_blocks += 1
            else:  # cut_vertex
                valid_nodes.add(node)
        else:
            if node_data.get('type') == 'block':
                pruned_blocks += 1
    
    print(f"\nBlocks kept: {kept_blocks}, Blocks pruned: {pruned_blocks}")
    print(f"Valid nodes: {len(valid_nodes)} / {initial_nodes}")
    
    # 7. Remove invalid nodes from the directed graph
    nodes_to_remove = set(G.nodes()) - valid_nodes
    G.remove_nodes_from(nodes_to_remove)
    
    # Also remove any newly isolated nodes
    isolates = list(nx.isolates(G))
    if isolates:
        G.remove_nodes_from(isolates)
        print(f"Removed {len(isolates)} isolated nodes")
    
    print(f"Pruned: {initial_nodes} → {len(G.nodes)} nodes, "
          f"{initial_edges} → {len(G.edges)} edges")
    
    return G




def get_valid_nodes(G, start_node):
    # important_nodes = get_nodes_with_edge_attribute_values(G, 'highway', {'primary', 'secondary', 'tertiary'})
    important_nodes = get_nodes_with_edge_attribute_values(G, 'highway', {'primary', 'secondary'})
    important_nodes = list(important_nodes)
    disp_imp = [[x] for x in important_nodes]
    ox.plot_graph_routes(G, disp_imp)

    queue = [((0, 0.0, start_node), PathNode(start_node), 0)]
    valid_nodes = important_nodes
    # print(f"Starting loop detection... range {min_path_length}-{max_path_length}m")
    
    iters = 0
    MAX_ITERS = 500000
    while queue:
        iters += 1
        if iters > MAX_ITERS:
            print(f"Max iterations {MAX_ITERS} reached. Stopping.")
            break
            
        dist, curr_node, visited_mask = heapq.heappop(queue)
        # ox.plot_graph_route(G, [curr_node.id], route_color='blue')
        if curr_node.id in valid_nodes:
            print("curr node in valid nodes")
            path = curr_node.traverse() 
            ox.plot_graph_route(G, path, route_color='pink')
            valid_nodes.update(path)
            list_valid_nodes = list(valid_nodes)
            show_valid = [[x] for x in list_valid_nodes]
            ox.plot_graph_routes(G, show_valid)
            continue
        # Detect loops when current node exists in visited mask
        elif (visited_mask & (1 << curr_node.id)):
            print("found new path")
            path_segment, loop_start = curr_node.traverse_to(curr_node.id)
            if not path_segment or not loop_start:
                continue

            loop_dist = dist - loop_start.dist
            if loop_dist < 10:
                continue

            out_back_section = loop_start.traverse() 
            path = path_segment + out_back_section
            ox.plot_graph_route(G, path, route_color='blue')
            valid_nodes.update(path)
            list_valid_nodes = list(valid_nodes)
            show_valid = [[x] for x in list_valid_nodes]
            ox.plot_graph_routes(G, show_valid)
            continue

        # Expand to neighbors
        new_mask = visited_mask | (1 << curr_node.id)
        
        for neighbor in G.neighbors(curr_node.id):
            if neighbor == getattr(curr_node.prev, 'id', None):
                continue  # Skip immediate backtracking

            # new_dist = weight_function(G, curr_node, neighbor, 0, dist)
            new_node = PathNode(neighbor, curr_node, new_dist)
            
            heapq.heappush(queue, (
                new_dist,
                new_node,
                new_mask
            ))

    return valid_nodes




if __name__ == "__main__":
    
    
    # 1. Download/Load 
    # graph_name = "boone_process_test"
    # graph_name = "boone_1600"
    # graph_name = "shelby_process_test"
    graph_name = "avl_1"
    # graph_name = "Vilas_process_test"
    # graph_name = "v_2_15_test02"
    saved_path = f"graphs/{graph_name}.gpickle" 
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    abs_saved_path = os.path.join(base_dir, saved_path)

    if os.path.exists(abs_saved_path):
        print(f"Using existing graph at {abs_saved_path}")
        saved_path = abs_saved_path
    elif os.path.exists(saved_path):
        print(f"Using existing graph at {saved_path}")
    else:
        # Download logic defined previously
        print("Downloading graph...")
        # lat1, lng1 = [36.2158714783487, -81.68045473827847]
        # lat1, lng1 = [36.26642986174743, -81.81297732128627]
        # lat1, lng1 = [35.61861243091474, -82.55423653308036]
        # lat2, lng2 = [35.626141, -82.550102]
        # lat1, lng1 = [35.626141, -82.550102]
        # lat1, lng1 = [36.253080, -81.141820]
        lat1, lng1 = [36.21955, -81.6806]



        radius = 16000
        

        # saved_path = download_test_graph_bbox(
        #     coords, graph_name, 
        #     simplify=True, 
        #     custom_filter='["highway"~"cycleway|path|primary|secondary|tertiary|residential|primary_link|secondary_link|tertiary_link|road|living_street|bridleway|path"]'
        # )
        center_point = (lat1, lng1)
        saved_path = download_test_graph_circle(
            center_point, radius, graph_name,
            simplify=True,
            custom_filter='["highway"~"cycleway|path|primary|secondary|tertiary|residential|primary_link|secondary_link|tertiary_link|road|living_street|bridleway|path"]'
        )
    
    G = get_graph(saved_path)
    
    if G:
        print(f"Successfully loaded {len(G.nodes)} nodes.")
        
        # Print attributes to see what we're working with
        print_unique_edge_attributes(G)
        # ox.plot_graph(G)
        
        # Run the iterative cleaning process
        G = process_graph(G)

        print(f"Final Graph has {len(G.nodes)} nodes and {len(G.edges)} edges.")
        
        # Test specific user request
        # highway_types = {'primary', 'secondary', 'tertiary'}
        # important_nodes = get_nodes_with_edge_attribute_values(G, 'highway', highway_types)
        # print(f"Number of nodes on primary/secondary/tertiary roads: {len(important_nodes)}")

        ox.plot_graph(G)
        # 8. Plot
        # try:
        #     plot_graph_colored_by_attribute(G, 'name')
        # except Exception as e:
        #     print(f"Could not plot: {e}")
        # else:
            # print("Graph already processed.")
            # print(len(G.nodes), len(G.edges))
            # G_proj = ox.projection.project_graph(G)
            # G2 = ox.simplification.consolidate_intersections(
            #     G_proj,
            #     rebuild_graph=True,
            #     tolerance=30,
            #     dead_ends=False,
            # )
            # print(len(G2.nodes), len(G2.edges))
            # G2 = G
            # ox.plot_graph(G2)
            # for u, v, k, data in G2.edges(keys=True, data=True):
                # print(u, v, k, data)
                # if 'ref' in data:
                    # print(u, v, k, data)



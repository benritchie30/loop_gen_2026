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
from shapely.geometry import LineString, MultiLineString

# Configuration
DEFAULT_GRAPH_PATH = 'graphs/asheville_test_small.gpickle'

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

def download_test_graph_bbox(north, south, east, west, name, network_type='all', **kwargs):
    """Downloads a graph from a bounding box and saves it. Accepts **kwargs for ox.graph_from_bbox."""
    print(f"Downloading graph '{name}' from bbox [N:{north}, S:{south}, E:{east}, W:{west}]...")
    try:
        G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type=network_type, **kwargs)
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

def remove_dead_ends(G):
    """
    Iteratively removes nodes that are dead ends (degree 1 in undirected representation)
    until no such nodes remain.
    """
    print("\n--- Removing Dead Ends (Iterative Pruning) ---")
    initial_nodes = len(G.nodes)
    
    iteration = 0
    while True:
        iteration += 1
        # User requested update: use ox.convert.to_undirected(G)
        try:
            G_undir = ox.convert.to_undirected(G)
        except AttributeError:
             # Fallback if older osmnx
             G_undir = ox.utils_graph.get_undirected(G)
             
        dead_end_nodes = [n for n, d in G_undir.degree() if d == 1]
        
        if not dead_end_nodes:
            break
            
        G.remove_nodes_from(dead_end_nodes)
        
        if iteration > 100:
            print("Max iterations reached.")
            break
            
    removed_count = initial_nodes - len(G.nodes)
    print(f"Finished pruning after {iteration} iterations. Total removed: {removed_count}. Remaining nodes: {len(G.nodes)}")
    return G

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
    return G

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

def simplify_topology(G):
    """
    Simplifies the graph topology by removing interstitial nodes (nodes with degree 2).
    This merges edges incident to such nodes into a single edge, summing length and merging geometry.
    
    AGGRESSIVE STRATEGY:
    Standard ox.simplify_graph() keeps nodes if edge attributes (like speed, name) change.
    To force simplification, we first STRIP all non-essential attributes from edges.
    """
    print(f"Simplifying graph topology (initial nodes: {len(G.nodes)})...")
    
    # 1. Strip non-essential attributes to allow merging
    print("Stripping edge attributes to force simplification...")
    # Attributes to KEEP (essential for routing/visualization)
    # 'highway' is needed for filtering/coloring
    # 'length' is needed for routing weight
    # 'geometry' is needed for shape
    # 'oneway' is needed for directionality
    keep_attrs = {'highway', 'length', 'geometry', 'oneway', 'reversed'}
    
    for u, v, k, data in G.edges(keys=True, data=True):
        keys_to_remove = [key for key in data.keys() if key not in keep_attrs]
        for key in keys_to_remove:
            del data[key]
            
        # Sanitize remaining attributes (convert lists to tuples/strings to make them hashable)
        for key in data.keys():
            val = data[key]
            if isinstance(val, list):
                # Convert list to tuple to be hashable (or string)
                data[key] = tuple(val)
            
    # 2. Reset simplification flag to force re-run
    # osmnx skips simplification if G.graph.get("simplified") is True.
    if "simplified" in G.graph:
        G.graph["simplified"] = False

    # 3. Run standard simplification
    try:
        # strict=True is default in newer osmnx/consolidated.
        # We rely on the fact that now attributes match, so it WILL merge.
        G = ox.simplify_graph(G)
    except Exception as e:
        print(f"Simplification failed: {e}")
    
    print(f"Graph simplified. Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")
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

if __name__ == "__main__":
    
    print("WARNING: Make sure to run this script in an environment with osmnx, networkx, matplotlib installed.")
    
    # 1. Download/Load 
    graph_name = "asheville_bbox_test"
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
        lats = [35.59560242663153, 35.639643142853984]
        lngs = [-82.53539085388185, -82.57435798645021]
        north = max(lats); south = min(lats); east = max(lngs); west = min(lngs)
        saved_path = download_test_graph_bbox(
            north, south, east, west, graph_name, 
            simplify=True, 
            custom_filter='["highway"~"cycleway|path|primary|secondary|tertiary|residential|primary_link|secondary_link|tertiary_link|road|living_street|bridleway|path"]'
        )
    
    G = get_graph(saved_path)
    
    if G:
        print(f"Successfully loaded {len(G.nodes)} nodes.")
        
        # Print attributes to see what we're working with
        print_unique_edge_attributes(G)
        
        # 2. Filter: Keep ONLY edges with 'highway' attr
        # G = filter_keep_only_attribute(G, 'highway')
        
        # 3. Filter: Keep only ALLOWED highway types (handled by custom_filter during download now, but kept as safety check/cleanup for loaded graphs)
        # If downloaded with custom_filter, these loops should find nothing to remove.
        target_types = {
             'cycleway', 'path', 
             'primary', 'secondary', 'tertiary', 'residential',
             'primary_link', 'secondary_link', 'tertiary_link', 
             'road', 'living_street', 'bridleway', 'path'
        }
        
        print(f"\n--- Verifying allowed highway types: {target_types} ---")
        edges_to_remove = []
        for u, v, k, data in G.edges(keys=True, data=True):
            hw = data.get('highway')
            keep = False
            
            def is_allowed(t): return t in target_types
            
            if isinstance(hw, list):
                if any(is_allowed(t) for t in hw): keep = True
            else:
                if is_allowed(hw): keep = True
            
            if not keep:
                edges_to_remove.append((u, v, k))
        
        if edges_to_remove:
            G.remove_edges_from(edges_to_remove)
            print(f"Removed {len(edges_to_remove)} edges due to disallowed highway type.")
        else:
            print("All edges conform to allowed highway types.")
            
        # 4. Remove Self Loops (Tiny loops connecting back to same node)
        G = remove_self_loops(G)

        
        # 6. Remove Dead Ends
        G = remove_dead_ends(G)
        ox.plot_graph(G)

        G.remove_nodes_from(list(nx.isolates(G)))
        print(f"Removed isolated nodes.")
        print("\n--- Simplifying Topology (Merging degree-2 nodes) ---")

        G = simplify_topology(G)

        print(f"Final Graph has {len(G.nodes)} nodes and {len(G.edges)} edges.")
        ox.plot_graph(G)
        # 8. Plot
        try:
            plot_graph_colored_by_attribute(G, 'highway')
        except Exception as e:
            print(f"Could not plot: {e}")




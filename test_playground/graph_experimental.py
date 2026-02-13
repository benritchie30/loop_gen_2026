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

def download_test_graph_bbox(north, south, east, west, name, network_type='all'):
    """Downloads a graph from a bounding box and saves it."""
    print(f"Downloading graph '{name}' from bbox [N:{north}, S:{south}, E:{east}, W:{west}]...")
    try:
        # Note: osmnx API change: bbox (north, south, east, west)
        G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type=network_type)
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

def download_test_graph(lat, lng, radius_meters, name, network_type='all'):
    """Downloads a graph from a point and saves it to test_playground/graphs."""
    print(f"Downloading graph '{name}' from ({lat}, {lng}) with radius {radius_meters}m...")
    try:
        G = ox.graph_from_point((lat, lng), dist=radius_meters, network_type=network_type)
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

def analyze_road_types(G):
    """Prints a count of all 'highway' values in the graph edges."""
    print("\n--- Road Type Analysis ---")
    highway_types = []
    # handling multigraph edges
    for u, v, k, data in G.edges(keys=True, data=True):
        hw = data.get('highway', None)
        if isinstance(hw, list):
            highway_types.extend(hw)
        elif hw:
            highway_types.append(hw)
    
    counts = Counter(highway_types)
    for hw_type, count in counts.most_common():
        print(f"{hw_type}: {count}")
    return counts

def filter_road_types(G, excluded_types):
    """Removes edges that match the excluded highway types."""
    print(f"\n--- Filtering Road Types: {excluded_types} ---")
    edges_to_remove = []
    for u, v, k, data in G.edges(keys=True, data=True):
        hw = data.get('highway', None)
        should_remove = False
        
        # Handle list of types (e.g. ['primary', 'residential'])
        if isinstance(hw, list):
            if any(t in excluded_types for t in hw):
                should_remove = True
        else:
            if hw in excluded_types:
                should_remove = True
                
        if should_remove:
            edges_to_remove.append((u, v, k))
            
    if edges_to_remove:
        G.remove_edges_from(edges_to_remove)
        print(f"Removed {len(edges_to_remove)} edges.")
        
    print(f"Graph now has {len(G.nodes)} nodes and {len(G.edges)} edges.")
    return G

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
        G_undir = ox.convert.to_undirected(G)
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

def analyze_edge_attributes(G):
    """Prints all unique attributes found in graph edges with example values."""
    print("\n--- Edge Attributes Analysis ---")
    all_keys = set()
    example_values = {}
    
    for u, v, k, data in G.edges(keys=True, data=True):
        for key, val in data.items():
            all_keys.add(key)
            if key not in example_values:
                example_values[key] = set()
            if len(example_values[key]) < 10: 
                val_str = str(val)
                example_values[key].add(val_str)
                
    print(f"Found {len(all_keys)} unique edge attributes:")
    for key in sorted(all_keys):
        examples = ", ".join(list(example_values[key])[:10])
        print(f"  - {key}: [{examples}, ...]")

def print_unique_attribute_values(G, attribute):
    """Prints all unique values for a specific edge attribute."""
    print(f"\n--- Unique Values for attribute '{attribute}' ---")
    values = set()
    found_any = False
    for u, v, k, data in G.edges(keys=True, data=True):
        if attribute in data:
            found_any = True
            val = data[attribute]
            if isinstance(val, list):
                for v_item in val:
                    values.add(v_item)
            else:
                values.add(val)
    
    if not found_any:
        print(f"Attribute '{attribute}' not found in any edges.")
        return

    sorted_values = sorted(list(values), key=lambda x: str(x))
    print(f"Found {len(sorted_values)} unique values:")
    for val in sorted_values:
        print(f"  - {val}")

def plot_edges_by_attribute(G, attribute, value=None):
    """
    Plots the graph. 
    If value is specified, only plots edges with that attribute value.
    If value is None, plots all edges.
    """
    if value is None:
        print(f"Plotting all edges (ignoring attribute '{attribute}' filter)...")
        # ox.plot_graph(G, show=True, node_size=0, edge_linewidth=0.5)
        # Using a distinct color for plotting 'all' in this mode to avoid confusion
        ox.plot_graph(G, show=True, node_size=0, edge_linewidth=0.5, edge_color='gray')
        return

    print(f"Plotting edges where {attribute} = {value}...")
    
    edges_to_keep = []
    for u, v, k, data in G.edges(keys=True, data=True):
        if attribute in data:
            val = data[attribute]
            if isinstance(val, list):
                if value in val:
                    match = True
            else:
                if val == value:
                    match = True
            
            if match:
                edges_to_keep.append((u, v, k))
    
    if not edges_to_keep:
        print(f"No edges found with {attribute} = {value}")
        return

    G_filtered = G.copy()
    all_edges = set(G.edges(keys=True))
    keep_edges = set(edges_to_keep)
    remove_edges = all_edges - keep_edges
    
    if remove_edges:
        G_filtered.remove_edges_from(remove_edges)
    
    # Optional: remove isolated nodes? Maybe better to leave them to see relative position?
    # Usually easier to see if we clean up.
    # G_filtered = ox.utils_graph.remove_isolated_nodes(G_filtered)
    
    print(f"Filtered graph has {len(G_filtered.edges)} edges.")
    if len(G_filtered.edges) > 0:
        ox.plot_graph(G_filtered, show=True, node_size=0, edge_linewidth=1.0, edge_color='red')
    else:
        print("Resulting graph has no edges.")

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
    
    # We need to map edges to their values for later updates
    edge_values = []
    
    for u, v, k, data in G.edges(keys=True, data=True):
        val = "MISSING"
        if attribute in data:
            raw_val = data[attribute]
            if isinstance(raw_val, list):
                val = raw_val[0]
            else:
                val = raw_val
        
        # Ensure value is string for consistency
        val_str = str(val)
        unique_values.add(val_str)
        counts[val_str] += 1
        edge_values.append(val_str)
            
    sorted_values = sorted(list(unique_values))
    
    # 2. Assign colors
    n_colors = len(sorted_values)
    # Using tab20 or spectral for variety
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
        
    # 4. Plot using ox.plot_graph to get the base figure
    # We need to capture the LineCollection object ox creates for edges
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
    
    # Get edge collection
    edge_collection = None
    for collection in ax.collections:
        # Heuristic: Edges collection has same specific count of paths
        if len(collection.get_paths()) == len(G.edges):
            edge_collection = collection
            break
            
    if edge_collection is None:
        print("Could not locate edge collection for interactivity.")
        plt.show()
        return

    # 5. Create Interactive Legend
    legend_lines = []
    
    # We create proxy artists for the legend
    for val in sorted_values:
        # Create a proxy line
        line = Line2D([0], [0], color=value_to_color[val], lw=4, label=f"{val} ({counts[val]})")
        legend_lines.append(line)
        
    # Create the legend
    leg = ax.legend(handles=legend_lines, loc='best', fontsize='x-small', title=attribute)

    # 6. Setup Interactivity
    # Store original colors
    # edge_collection.get_edgecolors() returns RGBA array
    # We can just use our derived list for resets
    
    def on_hover(event):
        # Only process if inside axes
        if event.inaxes != ax:
            return
            
        is_over_legend_item = False
        highlight_val = None
        
        # Check against legend texts
        for text in leg.get_texts():
            contains, _ = text.contains(event)
            if contains:
                is_over_legend_item = True
                label = text.get_text()
                # Find " ("
                split_idx = label.rfind(" (")
                if split_idx != -1:
                    highlight_val = label[:split_idx]
                break
        
        # Check against legend handles (lines) can be tricky as they are sometimes tiny proxys.
        # Often text is minimal hitting area.
        # But let's check bounding boxes of legend items if we wanted more precision.
        # For now, text hover is usually sufficient for standard matplotlib legends.

        if is_over_legend_item and highlight_val is not None:
            # Highlight this value
            new_colors = []
            new_widths = []
            for val, orig_col in zip(edge_values, edge_colors):
                if val == highlight_val:
                    new_colors.append(orig_col) # Keep original color
                    new_widths.append(3.0)      # Thicker
                else:
                    new_colors.append('#eeeeee') # Gray out others
                    new_widths.append(0.5)      # Thinner
            
            edge_collection.set_color(new_colors)
            edge_collection.set_linewidth(new_widths)
            fig.canvas.draw_idle()
            
        else:
            # Reset to normal state if we were highlighting (or just always reset)
            # Optimization: check if we need to reset
            # But safe to just reset
            edge_collection.set_color(edge_colors)
            edge_collection.set_linewidth(1.5)
            fig.canvas.draw_idle()

    # Connect event
    fig.canvas.mpl_connect('motion_notify_event', on_hover)
    
    plt.title(f"Graph colored by '{attribute}' (Hover over legend text to highlight)")
    plt.tight_layout()
    plt.show()

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
        
    print(f"Graph now has {len(G.nodes)} nodes and {len(G.edges)} edges.")
    return G


if __name__ == "__main__":
    
    print("WARNING: Make sure to run this script in an environment with osmnx, networkx, matplotlib installed.")
    
    # 1. Download New Test Graph (BBox)
    # Coordinates provided: 
    # Point 1: 35.59560242663153, -82.53539085388185
    # Point 2: 35.639643142853984, -82.57435798645021
    
    # Organize into N, S, E, W
    lats = [35.59560242663153, 35.639643142853984]
    lngs = [-82.53539085388185, -82.57435798645021]
    
    north = max(lats)
    south = min(lats)
    east = max(lngs)
    west = min(lngs)
    
    graph_name = "asheville_bbox_test"
    saved_path = f"graphs/{graph_name}.gpickle" 
    
    # Check absolute path just in case
    base_dir = os.path.dirname(os.path.abspath(__file__))
    abs_saved_path = os.path.join(base_dir, saved_path)

    # Use existing or download
    if os.path.exists(abs_saved_path):
        print(f"Using existing graph at {abs_saved_path}")
        saved_path = abs_saved_path
    elif os.path.exists(saved_path):
        print(f"Using existing graph at {saved_path}")
    else:
        # If not exists, download
        saved_path = download_test_graph_bbox(north, south, east, west, graph_name, network_type='all')
    
    G = get_graph(saved_path)
    
    if G:
        print(f"Successfully loaded {len(G.nodes)} nodes.")
        
        # 2. Filter: Keep ONLY edges that are "highways"
        # Since we downloaded network_type='all', it might include other things.
        # This step ensures we only keep things tagged as highways.
        G = filter_keep_only_attribute(G, 'highway')
        
        # 3. Filter: Keep only ALLOWED highway types
        # As requested by user:
        # cycleway, path, primary, secondary, tertiary, residential
        # primary/secondary/tertiary link
        
        #Include steps?
        target_types = {
             'cycleway', 'path', 
             'primary', 'secondary', 'tertiary', 'residential',
             'primary_link', 'secondary_link', 'tertiary_link', 'road', 'living_street',
            'birdleway', 'path'
        }
        
        print(f"\n--- Filtering to keep ONLY allowed highway types: {target_types} ---")
        edges_to_remove = []
        for u, v, k, data in G.edges(keys=True, data=True):
            hw = data.get('highway')
            keep = False
            
            # Helper to check if a single type string is allowed
            def is_allowed(t):
                 return t in target_types
            
            if isinstance(hw, list):
                # If ANY of the types in the list are allowed, we keep it.
                if any(is_allowed(t) for t in hw):
                    keep = True
            else:
                if is_allowed(hw):
                    keep = True
            
            if not keep:
                edges_to_remove.append((u, v, k))
        
        #Remove edges
        if edges_to_remove:
            G.remove_edges_from(edges_to_remove)
            print(f"Removed {len(edges_to_remove)} edges due to disallowed highway type.")


        remove_dead_ends(G)


        # 4. Cleanup Steps
        # A. Remove Safe Isolates (NetworkX method to avoid OSMnx error)
        G.remove_nodes_from(list(nx.isolates(G)))
        
        # B. Remove Self Loops
        # G = remove_self_loops(G)
        
        # C. Keep Only Largest Connected Component (Removes disjoint islands)
        # G = keep_only_largest_connected_component(G)
        
        # D. Prune Dead Ends (Iterative)
        # We do this LAST to prune back branches from the main component
        G = remove_dead_ends(G)
        
        # E. Final cleanup of isolates in case pruning left any
        
        G.remove_nodes_from(list(nx.isolates(G)))
        
        print(f"Final Graph has {len(G.nodes)} nodes and {len(G.edges)} edges.")
        
        # 4. Plot Colored by Highway
        try:
            plot_graph_colored_by_attribute(G, 'highway')
        except Exception as e:
            print(f"Could not plot: {e}")

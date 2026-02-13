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
# DEFAULT_GRAPH_PATH = 'graphs/asheville_test_small.gpickle'

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
        
    G = ox.utils_graph.remove_isolated_nodes(G)
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
            match = False
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
    Prints a legend mapping colors to values.
    """
    print(f"\n--- Plotting graph colored by attribute '{attribute}' ---")
    
    # 1. Collect all unique values for this attribute
    unique_values = set()
    # Also collect counts for legend
    counts = Counter()
    
    for u, v, k, data in G.edges(keys=True, data=True):
        if attribute in data:
            val = data[attribute]
            if isinstance(val, list):
                # For coloring, we just pick the primary (first) value if it's a list
                val = val[0]
            unique_values.add(val)
            counts[val] += 1
        else:
            unique_values.add("MISSING")
            counts["MISSING"] += 1
            
    sorted_values = sorted(list(unique_values), key=lambda x: str(x))
    
    # 2. Assign colors
    # Use matplotlib colormap
    # 'tab20' is good for categorical data up to 20 types
    n_colors = len(sorted_values)
    if n_colors <= 10:
        cmap = cm.get_cmap('tab10', n_colors)
    elif n_colors <= 20:
        cmap = cm.get_cmap('tab20', n_colors)
    else:
        # If we have too many, loop through a larger map or random
        cmap = cm.get_cmap('nipy_spectral', n_colors)
    
    value_to_color = {}
    print("\nLegend (Color Key):")
    print(f"{'Value':<30} | {'Color':<10} | {'Count':<5}")
    print("-" * 55)
    
    for idx, val in enumerate(sorted_values):
        rgba = cmap(idx) 
        # Convert to hex for legend printing/consistency
        hex_color = mcolors.to_hex(rgba)
        value_to_color[val] = hex_color
        print(f"{str(val):<30} | {hex_color:<10} | {counts[val]:<5}")
        
    # 3. Assign colors to edges
    edge_colors = []
    
    # We need to iterate edges in the exact order osmnx/nx plots them.
    # ox.plot_graph generally plots G.edges() in order.
    # To be safe, we pass edge_colors as a list matching G.edges() iteration order.
    
    for u, v, k, data in G.edges(keys=True, data=True):
        val = "MISSING"
        if attribute in data:
            raw_val = data[attribute]
            if isinstance(raw_val, list):
                 val = raw_val[0]
            else:
                 val = raw_val
        
        edge_colors.append(value_to_color.get(val, "#000000")) 
        
    # 4. Plot
    # We need to create a figure to add a legend to
    # ox.plot_graph returns (fig, ax) if show=False
    try:
        fig, ax = ox.plot_graph(
            G, 
            edge_color=edge_colors, 
            node_size=0, 
            edge_linewidth=1.5, 
            show=False, 
            close=False,
            bgcolor='white', # White background for better color visibility
            edge_alpha=0.8
        )
        
        # Create custom legend for the plot window
        legend_elements = []
        for val in sorted_values:
            legend_elements.append(
                Line2D([0], [0], color=value_to_color[val], lw=2, label=f"{val} ({counts[val]})")
            )
                
        # Position legend outside the plot area
        ax.legend(handles=legend_elements, loc='best', fontsize='x-small', title=attribute)
        
        plt.title(f"Graph Edges Colored by '{attribute}'")
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Error plotting graph: {e}")

if __name__ == "__main__":
    
    # 1. Load 
    graph_path = 'graphs/asheville_test_small.gpickle'
    G = get_graph(graph_path)
    
    if G:
        print(f"Successfully loaded {len(G.nodes)} nodes.")
        
        # 4. NEW: Color Plot - Plotting multiple attributes as requested
        attributes_to_plot = ['highway', 'ref', 'service', 'tunnel']
        
        for attr in attributes_to_plot:
            try:
                plot_graph_colored_by_attribute(G, attr)
            except Exception as e:
                print(f"Could not plot attribute '{attr}': {e}")

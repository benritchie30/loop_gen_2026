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
from shapely.geometry import Point, LineString, MultiLineString

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
                        last = curr
                        curr = neigbors[0]
                        intermediate_nodes.append(curr)
        elif len(neigbors) == 2:

            edges_merged_success = remove_node_and_merge(G, neigbors[0], intermediate_node, neigbors[1])
        else:
            print("outlier")
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

def custom_simplify_topology(G):
    """
    Simplifies the graph by merging edges at nodes with degree 2 (1 in, 1 out).
    Preserves geometry by concatenating LineStrings.
    """
    print("Running Custom Simplification...")
    
    # We iterate until no more nodes are removed in a pass
    nodes_removed_count = 0
    
    # Work on a snapshot of nodes. 
    # Modifications in the loop are reflected in G immediately.
    # We re-check degrees inside the loop to ensure strict correctness.
    for n in list(G.nodes()):
        # Check if node still exists (might have been removed if we did complex logic, though here we only remove n)
        if not G.has_node(n):
            continue
            
        # Strict Degree 2 Check: 1 In, 1 Out
        neigbors = list(G.neighbors(n))


        if len(neigbors)== 2:
            neigbors = list(G.neighbors(n))
            u = neigbors[0]
            v = neigbors[1]
            # Prevent collapsing self-loops or tiny loops
            if u == n or v == n or u == v:
                continue
                
            # Get Edge Data (u -> n)
            # Handle MultiDiGraph: get_edge_data returns {key: {attrs}}
            edges_u_n = G.get_edge_data(u, n)
            if not edges_u_n: continue 
            key_u = list(edges_u_n.keys())[0] # Take first edge
            attr_u = edges_u_n[key_u]
            
            # Get Edge Data (n -> v)
            edges_n_v = G.get_edge_data(n, v)
            if not edges_n_v: continue
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
                
            # Concatenate Coordinates: coords1 + coords2[1:] (skip duplicate 'n')
            # shapely coords are list of tuples (x, y)
            new_coords = list(geo1.coords)[:-1] + list(geo2.coords)
            new_geometry = LineString(new_coords)
            
            # 2. Merge Attributes
            new_attr = attr_u.copy()
            new_attr['geometry'] = new_geometry
            new_attr['length'] = attr_u.get('length', 0) + attr_v.get('length', 0)
            # 3. Modify Graph
            # Add new edge u->v
            G.remove_node(n)
            G.add_edge(u, v, **new_attr)
            
            # Remove intermediate node n
            # print(neigbors)
            # ox.plot_graph_routes(G, routes=[[u], [n], [v]], route_colors=['g', 'r', 'b'])
            
            
            nodes_removed_count += 1
        # elif len(neigbors) == 1:
            # print("self loop", n, list(G.neighbors(n)))
            # ox.plot_graph_route(G, route=[n])

    print(f"  Removed {nodes_removed_count} interstitial nodes")

    print(f"Custom Simplification Complete. Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")
    return G

def process_graph(G):
    """
    Iteratively cleans and simplifies the graph until stable.
    Cycle: Remove Self Loops -> Remove Dead Ends -> Simplify Topology -> Remove Isolates
    """
    # Projecting the graph does not seeem to fix the edge combining issue
    # print("Projecting graph to UTM for processing...")
    # G = ox.project_graph(G)
    
    # 1. Initial Type Filter (Safety)
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
    
    
    remove_self_loops(G)
    remove_dead_ends_v3(G)
    # 4. Remove Isolates
    G.remove_nodes_from(list(nx.isolates(G)))

    # 3. Simplify (Merge 2-degree nodes)
    ox.plot_graph(G)
    
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
    # graph_name = "boone_process_test"
    # graph_name = "shelby_process_test"
    graph_name = "Vilas_process_test"
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
        lat1, lng1 = [36.25389270584704, -81.78986549377443]

        radius = 8000
        

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
        # print_unique_edge_attributes(G)
        
        # Run the iterative cleaning process
        G = process_graph(G)

        print(f"Final Graph has {len(G.nodes)} nodes and {len(G.edges)} edges.")
        ox.plot_graph(G)
        # 8. Plot
        try:
            plot_graph_colored_by_attribute(G, 'name')
        except Exception as e:
            print(f"Could not plot: {e}")
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



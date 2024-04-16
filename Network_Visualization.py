import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pickle

# Load the saved graph
with open("player_network.pickle", "rb") as f:
    G = pickle.load(f)

# Adjusted edge alpha calculation for MultiDiGraph
#edge_alphas = [np.log(abs(G[u][v][key]['weight']) + 1) if 'weight' in G[u][v][key] else 0
               #for u, v, key in G.edges(keys=True)]

# Node colors and sizes
node_colors = ['red' if G.nodes[node]['role'] == 'pitcher' else 'blue' for node in G.nodes]
node_sizes = [np.log(abs(G.nodes[node].get('wpa', 1)) + 1) * 100 for node in G.nodes]  # Scaling node size

# Position layout
pos = nx.spring_layout(G, scale=2, k=0.15)  # Adjust k for node spacing

# Drawing the network
plt.figure(figsize=(15, 15))
nx.draw_networkx_edges(G, pos,  edge_color='grey', width=0.5) # alpha=edge_alphas,
nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes)

# Omitting labels for clarity
# nx.draw_networkx_labels(G, pos)  # This line is commented out to remove labels

# Show plot
plt.title('MLB Player Network')
plt.axis('off')  # Turn off the axis
plt.show()

import pandas as pd
import networkx as nx
import pickle

# Load the data
event_data = pd.read_csv('event_data.csv')
batter_stats = pd.read_csv('batter_stats.csv').set_index('batter')
pitcher_stats = pd.read_csv('pitcher_stats.csv').set_index('pitcher')

# Load the graph
with open("player_network.pickle", "rb") as f:
    G = pickle.load(f)


# Function to normalize and consolidate edge weights for a specific statistic
def normalize_and_consolidate_for_stat(G, weight_key):
    # Create a new graph to hold the normalized weights
    G_normalized = nx.DiGraph()

    # Filter edges to include only those corresponding to the specific statistic
    filtered_edges = [(u, v, data) for u, v, data in G.edges(data=True) if weight_key in data]

    # Sum the weights from filtered edges between each pair of nodes
    for u, v, data in filtered_edges:
        weight = abs(data[weight_key])  # Ensure all weights are non-negative
        if G_normalized.has_edge(u, v):
            G_normalized[u][v]['weight'] += weight
        else:
            G_normalized.add_edge(u, v, weight=weight)

    # Normalize the weights so the sum of outgoing edges for each node is 1
    for node in G_normalized:
        total_weight = sum(data['weight'] for _, _, data in G_normalized.out_edges(node, data=True))
        for _, nbr, data in G_normalized.out_edges(node, data=True):
            data['weight'] /= total_weight if total_weight > 0 else 1

    return G_normalized


# Normalize the graph for WPA, RE, and Score
G_wpa_normalized = normalize_and_consolidate_for_stat(G, 'wpa')
G_re_normalized = normalize_and_consolidate_for_stat(G, 're')
G_score_normalized = normalize_and_consolidate_for_stat(G, 'score')

# Apply PageRank to each normalized graph for WPA, RE, and Score
pagerank_wpa = nx.pagerank(G_wpa_normalized, alpha=0.85, weight='weight', max_iter=10000)
pagerank_re = nx.pagerank(G_re_normalized, alpha=0.85, weight='weight', max_iter=10000)
pagerank_score = nx.pagerank(G_score_normalized, alpha=0.85, weight='weight', max_iter=10000)

# Save the PageRank values as node attributes in the original graph
nx.set_node_attributes(G, pagerank_wpa, name='pagerank_wpa')
nx.set_node_attributes(G, pagerank_re, name='pagerank_re')
nx.set_node_attributes(G, pagerank_score, name='pagerank_score')

# Initialize lists to store edge weights
edge_weights_wpa = []
edge_weights_re = []
edge_weights_score = []

# Assign edge weights based on pagerank scores for WPA, RE, and Score
for u, v, data in G.edges(data=True):
    weight_wpa = pagerank_wpa.get(u, 0) * pagerank_wpa.get(v, 0)
    weight_re = pagerank_re.get(u, 0) * pagerank_re.get(v, 0)
    weight_score = pagerank_score.get(u, 0) * pagerank_score.get(v, 0)

    data['weight_wpa'] = weight_wpa
    data['weight_re'] = weight_re
    data['weight_score'] = weight_score

    edge_weights_wpa.append(weight_wpa)
    edge_weights_re.append(weight_re)
    edge_weights_score.append(weight_score)

# Find the maximum edge weight for each pagerank type
max_weight_wpa = max(edge_weights_wpa)
max_weight_re = max(edge_weights_re)
max_weight_score = max(edge_weights_score)

# Scale the edge weights for WPA, RE, and Score
for u, v, data in G.edges(data=True):
    data['weight_wpa_scaled'] = data['weight_wpa'] / max_weight_wpa
    data['weight_re_scaled'] = data['weight_re'] / max_weight_re
    data['weight_score_scaled'] = data['weight_score'] / max_weight_score

# Update batter_stats and pitcher_stats with PageRank scores
for node_id, data in G.nodes(data=True):
    if data['role'] == 'batter':
        if node_id in batter_stats.index:
            batter_stats.at[node_id, 'pagerank_wpa'] = data.get('pagerank_wpa', 0)
            batter_stats.at[node_id, 'pagerank_re'] = data.get('pagerank_re', 0)
            batter_stats.at[node_id, 'pagerank_score'] = data.get('pagerank_score', 0)
    elif data['role'] == 'pitcher':
        if node_id in pitcher_stats.index:
            pitcher_stats.at[node_id, 'pagerank_wpa'] = data.get('pagerank_wpa', 0)
            pitcher_stats.at[node_id, 'pagerank_re'] = data.get('pagerank_re', 0)
            pitcher_stats.at[node_id, 'pagerank_score'] = data.get('pagerank_score', 0)

# Combine batter and pitcher stats
combined_stats = pd.concat([batter_stats, pitcher_stats], axis=0)

# Reset index and rename index column to 'player_id'
combined_stats.reset_index(inplace=True)
combined_stats.rename(columns={'index': 'player_id'}, inplace=True)

# Add a new column 'role' to denote player role (batter or pitcher)
combined_stats['role'] = combined_stats.apply(
    lambda row: 'batter' if row['player_id'] in batter_stats.index else 'pitcher', axis=1)

# Save the combined player stats
combined_stats.to_csv('combined_player_stats.csv', index=False)


def update_team_stats(team_stats_file, combined_player_stats_file, output_csv_file):
    # Read team statistics CSV file
    team_stats = pd.read_csv(team_stats_file)

    # Read combined player statistics CSV file
    combined_player_stats = pd.read_csv(combined_player_stats_file)

    # Group by team and sum up WPA, RE, and AAV
    player_grouped = combined_player_stats.groupby('team').agg({
        'pagerank_wpa': 'sum',
        'pagerank_re': 'sum',
        'aav': 'sum'  # Sum of AAV for each team
    }).reset_index()

    # Merge the summed values with the team stats
    team_stats = pd.merge(team_stats, player_grouped, on='team', how='left')

    # Save updated team statistics to a new CSV file
    team_stats.to_csv(output_csv_file, index=False)


# File paths
team_stats_file = 'team_stats.csv'
output_csv_file = 'updated_team_stats.csv'
combined_player_stats_file = 'combined_player_stats.csv'

# Update team statistics and plot bar charts
update_team_stats(team_stats_file, combined_player_stats_file, output_csv_file)

# Save the updated graph
with open("updated_network.pickle", "wb") as f:
    pickle.dump(G, f)

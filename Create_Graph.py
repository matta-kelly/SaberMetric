import pandas as pd
import networkx as nx
import pickle

## Load the data
event_data = pd.read_csv('event_data.csv')
batter_stats = pd.read_csv('batter_stats.csv').set_index('batter')
pitcher_stats = pd.read_csv('pitcher_stats.csv').set_index('pitcher')

# Initialize a multi-directed graph
G = nx.MultiDiGraph()

# Add player nodes with cumulative stats
for batter_id, batter_row in batter_stats.iterrows():
    batter_data = batter_row.to_dict()
    G.add_node(batter_id, **batter_data, role='batter')
    print(f"Added batter node: {batter_id}, Data: {batter_data}")

for pitcher_id, pitcher_row in pitcher_stats.iterrows():
    pitcher_data = pitcher_row.to_dict()
    G.add_node(pitcher_id, **pitcher_data, role='pitcher')
    print(f"Added pitcher node: {pitcher_id}, Data: {pitcher_data}")

# Dictionary to aggregate statistical measures for each pair of players
matchup_stats = {}

# Iterate over events
for _, row in event_data.iterrows():
    batter_id = row['batter']
    pitcher_id = row['pitcher']
    batter_wpa = row['batter_wpa']
    batter_delta_re = row['batter_delta_re']
    batter_score = row['batter_score']

    # Update aggregated statistics for each batter-pitcher matchup
    matchup_key = (batter_id, pitcher_id)
    if matchup_key not in matchup_stats:
        matchup_stats[matchup_key] = {
            'wpa': 0,
            're': 0,
            'score': 0
        }

    # Add batter's statistics to the matchup
    matchup_stats[matchup_key]['wpa'] += batter_wpa
    matchup_stats[matchup_key]['re'] += batter_delta_re
    matchup_stats[matchup_key]['score'] += batter_score

# Create directed edges based on aggregated statistical differences
for (batter_id, pitcher_id), stats in matchup_stats.items():
    wpa = stats['wpa']
    re = stats['re']
    score = stats['score']

    # Add directed edges for each statistic
    if wpa > 0:
        G.add_edge(pitcher_id, batter_id, wpa=wpa)
    elif wpa < 0:
        G.add_edge(batter_id, pitcher_id, wpa=wpa)

    if re > 0:
        G.add_edge(pitcher_id, batter_id, re=re)
    elif re < 0:
        G.add_edge(batter_id, pitcher_id, re=re)

    if score > 0:
        G.add_edge(pitcher_id, batter_id, score=score)
    elif score < 0:
        G.add_edge(batter_id, pitcher_id, score=score)


def check_edges(graph):
    for u, v in graph.edges():
        if graph.number_of_edges(u, v) > 3:
            print(f"Error: {u} -> {v} has more than 3 edges.")


check_edges(G)

# Save the graph
with open("player_network.pickle", "wb") as f:
    pickle.dump(G, f)

# Print a summary of the graph
print(f"Graph created with {len(G.nodes)} nodes and {len(G.edges)} edges.")

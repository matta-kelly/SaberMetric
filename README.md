# MLB Pitcher-Batter Network Analysis

## Project Overview
This project utilizes Statcast pitch data to perform a network analysis of MLB pitchers and batters. It leverages statistical measures such as Win Probability Added (WPA) and Run Expectancy (RE) to analyze player performance using a PageRank algorithm. The goal is to identify key players and understand the dynamics of player interactions throughout the season.

## Features
- **Data Import:** Fetch and preprocess Statcast event data. 
- **Statistical Analysis:** Calculate cumulative stats like WPA and RE for each player and team
- **Network Analysis:** Construct a network graph where nodes represent players and edges represent performance metrics.
- **PageRank Calculation:** Apply PageRank to assess the importance of players in the network based on their performance metrics.

## Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites
Before running the project, ensure you have the following installed:
- Python 3.8+
- Pandas
- Numpy
- NetworkX
- PyBaseball
- Matplotlib
- Pickle

## Files Description

### `Import.py`
This script is responsible for fetching and preprocessing Statcast pitch data from the specified MLB season. Key operations include:
- **Data Fetching:** Using the `pybaseball` library, it retrieves event data between specified dates.
- **Preprocessing:** Filters out incomplete records, normalizes player names using `unidecode`, and prepares several datasets for further analysis.
- **Data Export:** Outputs a filtered event dataset to `2023_mlb_event_data.csv` and performs initial calculations of Win Probability Added (WPA) and Run Expectancy (RE) for further use.

### `Create_Graph.py`
Builds a directed multigraph representing the interactions between pitchers and batters:
- **Data Loading:** Reads the preprocessed CSV files to retrieve player statistics.
- **Graph Construction:** Utilizes `NetworkX` to create nodes for each player (pitchers and batters) and edges that represent game events.
- **Node and Edge Attributes:** Each node stores player stats, and edges are weighted by performance metrics (WPA, RE, scores from events).
- **Graph Serialization:** Saves the graph to a file `player_network.pickle` for use in subsequent analysis.

### `PageRank.py`
Applies the PageRank algorithm to the network to identify influential players:
- **Graph Loading:** Loads the network graph from the pickle file.
- **PageRank Calculation:** Computes PageRank scores for each player using their on-field interactions and statistics like WPA and RE.
- **Normalization:** Adjusts the PageRank scores and recalculates them to ensure consistency across different performance metrics.
- **Results Saving:** Updates the graph with new PageRank scores and saves the updated graph back to a pickle file.

### `Network_Visualization.py`
Handles the visualization of the network graph created and analyzed in previous steps:
- **Graph Loading:** Retrieves the graph from the pickle file.
- **Visualization Setup:** Configures node sizes and colors based on player roles and performance metrics.
- **Drawing the Graph:** Uses `matplotlib` to draw nodes, edges, and labels.
- **Display Output:** Renders the graph visually on screen, helping to interpret the complex relationships and player impacts visually.


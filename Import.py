import pandas as pd
import numpy as np
import pybaseball as py
import unidecode

# Importing all event data
py.cache.enable()
# Fetching and preprocessing the data
data = py.statcast('2023-03-30', '2023-04-30')  # march 30 to october 1st for 2023...change dates as needed
df_filtered = data.dropna(subset=['events'])
df_filtered.to_csv('2023_mlb_event_data.csv', index=False)


# Function to normalize names by stripping spaces, converting to upper case and removing accents
def normalize_name(name):
    return unidecode.unidecode(name.strip().upper())


# Load and preprocess payroll data
payroll_data = pd.read_csv('payroll_2023.csv')
payroll_data['name'] = payroll_data['name'].str.upper().str.strip()

# Fetching and preprocessing the player stats data
df = pd.read_csv('C:/Users/matta/PycharmProjects/SaberMetric/2023_mlb_event_data.csv')

# Specify the columns that are necessary before transformations
required_columns = [
    'batter', 'pitcher', 'events', 'delta_home_win_exp', 'delta_run_exp',
    'inning_topbot', 'game_pk', 'home_team', 'away_team',
    'at_bat_number', 'pitch_number', 'post_home_score', 'post_away_score'
]

# Keep only the required columns in df
df = df[required_columns]

# Extract unique batter and pitcher IDs
batter_ids = df['batter'].unique()
pitcher_ids = df['pitcher'].unique()
game_pk = df['game_pk']

# Initialize batter and pitcher stats dataframes
batter_stats_df = pd.DataFrame(columns=['player_id', 'team', 'cumulative_wpa', 'cumulative_re', 'cumulative_score'])
pitcher_stats_df = pd.DataFrame(columns=['player_id', 'team', 'cumulative_wpa', 'cumulative_re', 'cumulative_score'])


def get_team_for_player(player_as_batter, player_as_pitcher):
    teams = set()
    for _, row in player_as_batter.iterrows():
        if row['inning_topbot'] == 'Top':
            teams.add(row['away_team'])
        else:
            teams.add(row['home_team'])

    for _, row in player_as_pitcher.iterrows():
        if row['inning_topbot'] == 'Top':
            teams.add(row['home_team'])
        else:
            teams.add(row['away_team'])

    # Handling the case of multiple teams if player switched teams during the season
    if len(teams) > 1:
        # This can be replaced with any logic you prefer
        # Maybe choose the most recent team or the one with the most occurrences
        return 'Multiple'
    elif len(teams) == 1:
        return teams.pop()  # The only team the player played for
    else:
        return 'Unknown'  # In case there's no data for the player


# Fetch player info and associate players with teams
player_name_cache = {}
player_team_association = {}  # New dictionary to keep track of player team associations

for player_id in np.concatenate([batter_ids, pitcher_ids]):
    player_info = py.playerid_reverse_lookup([player_id], key_type='mlbam')
    last_name, first_name = 'Unknown', ''
    if not player_info.empty:
        last_name, first_name = player_info.iloc[0][['name_last', 'name_first']]
    name = f"{last_name}, {first_name}"
    normalized_name = normalize_name(name)
    player_name_cache[player_id] = normalized_name

    # Separate dataframe slices for instances where this player was batting or pitching
    player_as_batter = df[df['batter'] == player_id]
    player_as_pitcher = df[df['pitcher'] == player_id]

    # Get the team association using the function defined above
    team = get_team_for_player(player_as_batter, player_as_pitcher)

    # Now store this in the player_team_association dictionary
    player_team_association[player_id] = team

    # Match and add AAV
    matching_row = payroll_data[payroll_data['name'] == normalized_name]
    if not matching_row.empty:
        aav = matching_row['aav'].values[0]
        aav = aav.replace('$', '').replace(',', '')  # Remove dollar sign and commas
        aav_value = float(aav)
    else:
        print(f"No AAV found for player: {normalized_name}")
        aav_value = 720000  # Set default AAV if player not found

    # Create a new row for the player including the AAV
    player_row = pd.DataFrame({
        'player_id': [player_id],
        'name': [name],  # Using the unnormalized name here for consistency with your first code snippet
        'team': [team],
        'cumulative_wpa': [0],
        'cumulative_re': [0],
        'cumulative_score': [0],
        'aav': [aav_value]  # Adding the AAV value
    })

    # Append to the respective dataframe
    if player_id in batter_ids:
        batter_stats_df = pd.concat([batter_stats_df, player_row], ignore_index=True)
    if player_id in pitcher_ids:
        pitcher_stats_df = pd.concat([pitcher_stats_df, player_row], ignore_index=True)

# Define the scoring system
event_scores = {
    'strikeout': -0.336210, 'field_out': -0.2, 'single': 0.9, 'home_run': 2,
    'walk': 0.65, 'fielders_choice_out': -0.2, 'double': 1.4, 'sac_bunt': 0,
    'force_out': -0.2, 'grounded_into_double_play': 0, 'hit_by_pitch': 0.67,
    'sac_fly': -0.1, 'fielders_choice': -0.3, 'triple': 1.9, 'caught_stealing_2b': 0,
    'other_out': -0.2, 'field_error': 0, 'double_play': -0.3, 'catcher_interf': 0,
    'strikeout_double_play': -0.33
}


# Function to score events
def score_event(event):
    return event_scores.get(event, 0)


# Assign WPA, RE, and Score to Batters and Pitchers
def assign_wpa_re_score(row):
    event = row['events']
    score = score_event(event)
    delta_wpa, delta_re = row['delta_home_win_exp'], row['delta_run_exp']
    inning = row['inning_topbot']
    # If the inning is Top, the away team is batting
    # If delta_wpa is positive, it means the home team's win probability increased, and vice versa.
    batter_wpa, pitcher_wpa = (-delta_wpa, delta_wpa) if inning == 'Top' else (delta_wpa, -delta_wpa)
    batter_re, pitcher_re = (-delta_re, delta_re) if inning == 'Top' else (delta_re, -delta_re)
    batter_score, pitcher_score = (score, -score) if inning == 'Bottom' else (-score, score)
    return (batter_wpa, pitcher_wpa, batter_re, pitcher_re, batter_score, pitcher_score)


df[['batter_wpa', 'pitcher_wpa', 'batter_delta_re', 'pitcher_delta_re', 'batter_score', 'pitcher_score']] = df.apply(
    assign_wpa_re_score, axis=1, result_type="expand")

'''
not using for now too slow

    
# Ensure 'player_id' is the index for batter_stats_df and pitcher_stats_df
batter_stats_df.set_index('player_id', inplace=True)
pitcher_stats_df.set_index('player_id', inplace=True)

# Group by 'batter' and calculate cumulative sums
batter_groups = df.groupby('batter')['batter_wpa', 'batter_delta_re', 'batter_score'].sum()

# Update batter_stats_df with the sums
batter_stats_df.update(batter_groups, overwrite=False)

# Group by 'pitcher' and calculate cumulative sums
pitcher_groups = df.groupby('pitcher')['pitcher_wpa', 'pitcher_delta_re', 'pitcher_score'].sum()

# Update pitcher_stats_df with the sums
pitcher_stats_df.update(pitcher_groups, overwrite=False)

# Reset index
batter_stats_df.reset_index(inplace=True)
pitcher_stats_df.reset_index(inplace=True)
'''

# Update Batter and Pitcher Stats
for _, row in df.iterrows():
    batter_id = row['batter']
    pitcher_id = row['pitcher']

    batter_stats_df.loc[batter_stats_df['player_id'] == batter_id, 'cumulative_wpa'] += row['batter_wpa']
    batter_stats_df.loc[batter_stats_df['player_id'] == batter_id, 'cumulative_re'] += row['batter_delta_re']
    batter_stats_df.loc[batter_stats_df['player_id'] == batter_id, 'cumulative_score'] += row['batter_score']

    pitcher_stats_df.loc[pitcher_stats_df['player_id'] == pitcher_id, 'cumulative_wpa'] += row['pitcher_wpa']
    pitcher_stats_df.loc[pitcher_stats_df['player_id'] == pitcher_id, 'cumulative_re'] += row['pitcher_delta_re']
    pitcher_stats_df.loc[pitcher_stats_df['player_id'] == pitcher_id, 'cumulative_score'] += row['pitcher_score']


# Determine Game Outcomes and Aggregate Stats
def determine_game_outcomes(df):
    last_pitches = df.sort_values(['game_pk', 'at_bat_number', 'pitch_number']).drop_duplicates('game_pk', keep='last')
    game_results = []
    for _, last_pitch in last_pitches.iterrows():
        game_pk, home_team, away_team = last_pitch['game_pk'], last_pitch['home_team'], last_pitch['away_team']
        home_points, away_points = last_pitch['post_home_score'], last_pitch['post_away_score']
        winner = home_team if home_points > away_points else away_team

        # Get the sum of the WPA, RE, and Score for batters and pitchers
        game_df = df[df['game_pk'] == game_pk]
        home_batter_wpa = game_df[game_df['inning_topbot'] == 'Bot']['batter_wpa'].sum()
        away_batter_wpa = game_df[game_df['inning_topbot'] == 'Top']['batter_wpa'].sum()
        home_pitcher_wpa = game_df[game_df['inning_topbot'] == 'Top']['pitcher_wpa'].sum()
        away_pitcher_wpa = game_df[game_df['inning_topbot'] == 'Bot']['pitcher_wpa'].sum()

        home_team_wpa = home_batter_wpa + home_pitcher_wpa
        away_team_wpa = away_batter_wpa + away_pitcher_wpa

        # Repeat the same for RE and Score
        home_batter_re = game_df[game_df['inning_topbot'] == 'Bot']['batter_delta_re'].sum()
        away_batter_re = game_df[game_df['inning_topbot'] == 'Top']['batter_delta_re'].sum()
        home_pitcher_re = game_df[game_df['inning_topbot'] == 'Top']['pitcher_delta_re'].sum()
        away_pitcher_re = game_df[game_df['inning_topbot'] == 'Bot']['pitcher_delta_re'].sum()

        home_team_re = home_batter_re + home_pitcher_re
        away_team_re = away_batter_re + away_pitcher_re

        home_batter_score = game_df[game_df['inning_topbot'] == 'Bot']['batter_score'].sum()
        away_batter_score = game_df[game_df['inning_topbot'] == 'Top']['batter_score'].sum()
        home_pitcher_score = game_df[game_df['inning_topbot'] == 'Top']['pitcher_score'].sum()
        away_pitcher_score = game_df[game_df['inning_topbot'] == 'Bot']['pitcher_score'].sum()

        home_team_score = home_batter_score + home_pitcher_score
        away_team_score = away_batter_score + away_pitcher_score

        game_results.append({
            'game_pk': game_pk,
            'home_team': home_team,
            'away_team': away_team,
            'home_points': home_points,
            'away_points': away_points,
            'winner': winner,
            'home_team_wpa': home_team_wpa,
            'away_team_wpa': away_team_wpa,
            'home_team_re': home_team_re,
            'away_team_re': away_team_re,
            'home_team_score': home_team_score,
            'away_team_score': away_team_score
        })

    return pd.DataFrame(game_results)


game_results = determine_game_outcomes(df)

# Aggregate Team Stats
teams = pd.concat([df['home_team'], df['away_team']]).unique()
team_stats = {}
for team in teams:
    team_batters = batter_stats_df[batter_stats_df['team'] == team]['player_id']
    team_pitchers = pitcher_stats_df[pitcher_stats_df['team'] == team]['player_id']

    # Sum of WPA, RE, and Score for both batters and pitchers
    total_wpa = batter_stats_df[batter_stats_df['player_id'].isin(team_batters)]['cumulative_wpa'].sum() + \
                pitcher_stats_df[pitcher_stats_df['player_id'].isin(team_pitchers)]['cumulative_wpa'].sum()
    total_re = batter_stats_df[batter_stats_df['player_id'].isin(team_batters)]['cumulative_re'].sum() + \
               pitcher_stats_df[pitcher_stats_df['player_id'].isin(team_pitchers)]['cumulative_re'].sum()
    total_score = batter_stats_df[batter_stats_df['player_id'].isin(team_batters)]['cumulative_score'].sum() + \
                  pitcher_stats_df[pitcher_stats_df['player_id'].isin(team_pitchers)]['cumulative_score'].sum()

    team_stats[team] = {
        'total_wpa': total_wpa,
        'total_re': total_re,
        'total_score': total_score,
        'wins': 0,  # This will be updated in the next step
        'losses': 0  # This will be updated in the next step
    }

# Updating the wins and losses for each team
for index, row in game_results.iterrows():
    winning_team = row['winner']
    losing_team = row['home_team'] if row['home_team'] != winning_team else row['away_team']
    team_stats[winning_team]['wins'] += 1
    team_stats[losing_team]['losses'] += 1

team_stats_df = pd.DataFrame.from_dict(team_stats, orient='index')

# Rename the player_id column to batter_id for the batters/pitchers DataFrame
batter_stats_df.rename(columns={'player_id': 'batter'}, inplace=True)
pitcher_stats_df.rename(columns={'player_id': 'pitcher'}, inplace=True)

# Count occurrences for each batter and pitcher in the event data
batter_occurrences = df['batter'].value_counts()
pitcher_occurrences = df['pitcher'].value_counts()

# Filter out batters and pitchers with fewer than 100 occurrences
eligible_batters = batter_occurrences[batter_occurrences >= 100].index
eligible_pitchers = pitcher_occurrences[pitcher_occurrences >= 100].index

# Update batter and pitcher stats dataframes to include only eligible players
batter_stats_df = batter_stats_df[batter_stats_df['batter'].isin(eligible_batters)]
pitcher_stats_df = pitcher_stats_df[pitcher_stats_df['pitcher'].isin(eligible_pitchers)]

# Update event data to only include events with eligible batters and pitchers
df = df[df['batter'].isin(eligible_batters) & df['pitcher'].isin(eligible_pitchers)]

# Step 16: Saving Processed Data
df.to_csv('event_data.csv', index=False)
batter_stats_df.to_csv('batter_stats.csv', index=False)
pitcher_stats_df.to_csv('pitcher_stats.csv', index=False)
game_results.to_csv('game_results.csv', index=False)
team_stats_df.to_csv('team_stats.csv', index_label='team')

from PitchFX import refresh_season_stats, find_games
import requests
import numpy as np
import os


def write_bullpen(bullpen, game_key_list):
    with open(os.path.join(os.getcwd(), "Bullpens", "Master Bullpen.csv"), 'w+') as file:
        file.write(",".join([str(k) for k in game_key_list]))
        file.write("\n")
        for pitcher in bullpen:
            file.write(f"{pitcher}\n")
            for inning_appearances in bullpen[pitcher]:
                file_appearances = ",".join([str(app) for app in inning_appearances])
                file.write(f"{file_appearances}\n")


def load_bullpen():
    bullpens = {}
    with open(os.path.join(os.getcwd(), "Bullpens", "Master Bullpen.csv")) as file:
        lines = file.readlines()
        if len(lines) < 2:
            return bullpens, []
        game_key_list = [int(k.strip()) for k in lines[0].split(",")]
        lines = lines[1:]
        for i in range(int(len(lines) / 8)):
            curr_pitcher = lines[i * 8].split(",")[0].strip()
            appearance_matrix = lines[i * 8 + 1:(i + 1) * 8]
            bullpens[curr_pitcher] = [[int(float(app.strip())) for app in line.split(",")] for line in appearance_matrix]
    return bullpens, game_key_list


def create_bullpen(single_day, day):
    if single_day:
        bullpen, game_key_list = load_bullpen()
        games = find_games(day)
    else:
        games = refresh_season_stats(day)
        bullpen = {}
        game_key_list = []
    for i, game in enumerate(games):
        game_key = game[1]
        if game_key in game_key_list:
            continue
        print(f"Creating bullpen for game {i + 1} of {len(games)}")
        play_by_play = requests.get(f"https://statsapi.mlb.com/api/v1/game/{game_key}/playByPlay").json()
        game_key_list.append(game_key)
        for play in play_by_play["allPlays"]:
            action_index = play["actionIndex"]
            if len(action_index) == 0:
                continue
            for action in action_index:
                event = play["playEvents"][action]
                if event["details"]["eventType"] == "pitching_substitution":
                    new_pitcher = event["player"]["id"]
                    inning = play["about"]["inning"]
                    lead = calc_score_diff(play, event)
                    lead = -5 if lead < -4 else 5 if lead > 4 else lead
                    inning = 4 if inning <= 4 else 10 if inning >= 10 else inning
                    if new_pitcher not in bullpen:
                        bullpen[new_pitcher] = np.zeros((7, 11), dtype=int)
                    bullpen[new_pitcher][inning - 4][lead + 5] += 1
    return bullpen, game_key_list


def get_roster_player_keys(day, id_is_key):
    roster = {}
    team_list = get_team_list(day.year)[0]
    for year in range(day.year - 2, day.year + 1):
        params = {"rosterType": "fullRoster", "season": year}
        for team in team_list:
            json_roster = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{team}/roster", params=params).json()
            for player in json_roster["roster"]:
                if player["person"]["id"] not in roster and player["person"]["fullName"] not in roster:
                    if id_is_key:
                        roster[player["person"]["id"]] = player["person"]["fullName"]
                    else:
                        roster[player["person"]["fullName"]] = player["person"]["id"]
    return roster


def get_team_list(year):
    url = f"https://statsapi.mlb.com/api/v1/teams?season={year}"
    teams = requests.get(url).json()
    team_list = []
    team_names = []
    for team in teams["teams"]:
        if team["sport"]["id"] != 1:
            continue
        team_list.append(team["id"])
        team_names.append(team["teamName"])
    return team_list, team_names


def calc_score_diff(play, event):
    if play["about"]["isTopInning"]:
        return event["details"]["homeScore"] - event["details"]["awayScore"]
    else:
        return event["details"]["awayScore"] - event["details"]["homeScore"]

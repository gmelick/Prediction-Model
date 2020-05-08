import requests
from bs4 import BeautifulSoup
import numpy as np
from datetime import timedelta
from PitchFX import find_games, refresh_season_stats
import os


def process_day(day):
    yesterday_games = find_games(day)
    __create_roster(day)
    if day.month >= 5:
        __bullpens_to_file(day.year)
    else:
        __bullpens_to_file(day.year - 1)
    __pitches_to_file(yesterday_games, False)


def refresh_season(day):
    games = refresh_season_stats(day)
    __pitches_to_file(games, True)


def __create_roster(day):
    cur_date = day - timedelta(1)
    roster = {}
    # Load pre-existing players into roster
    with open(os.path.join(cwd, "Master Roster.csv")) as file:
        player_list = [line.split(",")[0].strip() for line in file.readlines()]

    # Get new players from previous day's games and load them into roster
    url = f"https://www.mlb.com/starting-lineups/{cur_date}"
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    games = soup.find_all("div",
                          {"class": "starting-lineups__teams starting-lineups__teams--sm starting-lineups__teams--xl"})
    for i, game in enumerate(games):
        for player in game.find_all("a", {"class": "starting-lineups__player--link"}):
            if player.text not in player_list:
                href = player["href"]
                player_number = href[href.rfind("-") + 1:]
                roster[player.text] = player_number

    # Write the roster to file
    with open(os.path.join(cwd, "Master Roster.csv"), 'a+') as file:
        for player in roster:
            file.write(f"{player},{roster[player]}\n")
    return roster


def __bullpens_to_file(year):
    for i, team in enumerate(__teams):
        composite, bullpen = __get_bullpen(team, year)
        with open(os.path.join(cwd, "Bullpens", f"{year} {team} Bullpen.csv"), 'w+') as file:
            for pitcher in bullpen:
                pitcher_write = name_corrections[pitcher] if pitcher in name_corrections else pitcher
                file.write(f"{pitcher_write}\n")
                __write_matrix_to_file(bullpen[pitcher], file)
            file.write("Composite\n")
            __write_matrix_to_file(composite, file)


def __write_matrix_to_file(matrix, file):
    for row in matrix:
        file_write_row = ",".join([str(entry) for entry in row])
        file.write(f"{file_write_row}\n")


def __get_bullpen(team_name, year):
    __pitchers = {}
    __comp_matrix = np.zeros((7, 11))

    url = f"https://www.baseball-reference.com/teams/{__teams[team_name]}/{year}-pitching.shtml"
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    rows = soup.find("table", {"id": "team_pitching"}).find("tbody").find_all("tr")
    for row in rows:
        __process_player(row, year, __pitchers, __comp_matrix)
    return __comp_matrix, __pitchers


def __process_player(row, year, __pitchers, __comp_matrix):
    position = row.find("td", {"data-stat": "pos"})
    if position is not None:
        innings = float(row.find("td", {"data-stat": "IP"}).text.strip())
        if position.text.strip() != "SP" and innings >= 15:
            situations = __get_pitcher_situations(row, year)
            name = row.find("a").text.strip()
            __pitchers[name], __comp_matrix = __create_matrix(situations, __pitchers, __comp_matrix)


def __get_pitcher_situations(row, year):
    link = row.find("a")["href"]
    player_id = link[link.rfind("/") + 1: link.rfind(".")]
    params = {"id": player_id, "t": "p", "year": year}
    soup = BeautifulSoup(requests.get("https://www.baseball-reference.com/players/gl.fcgi", params).content,
                         'html.parser')
    return soup.find("table", {"id": "pitching_gamelogs"}).find("tbody").find_all("td",
                                                                                  {"data-stat": "pitcher_situation_in"})


def __create_matrix(situations, __pitchers, __comp_matrix):
    pitcher_matrix = np.zeros((7, 11))
    for situation in situations:
        if "1b start" not in situation.text and "1t start" not in situation.text:
            inning = int(situation.text[:2])
            if inning != 0:
                score = situation.text[situation.text.rfind("out") + 4:]
                pitcher_matrix, __comp_matrix = __fill_matrix(inning, score, pitcher_matrix, __comp_matrix)
    return pitcher_matrix, __comp_matrix


def __fill_matrix(inning, score, pitcher_matrix, __comp_matrix):
    if inning <= 4:
        pitcher_matrix, __comp_matrix = __fill_runs(0, score, pitcher_matrix, __comp_matrix)
    elif inning >= 10:
        pitcher_matrix, __comp_matrix = __fill_runs(6, score, pitcher_matrix, __comp_matrix)
    else:
        pitcher_matrix, __comp_matrix = __fill_runs(inning - 4, score, pitcher_matrix, __comp_matrix)
    return pitcher_matrix, __comp_matrix


def __fill_runs(index, score, pitcher_matrix, __comp_matrix):
    if score == "tie":
        pitcher_matrix, __comp_matrix = __iter_indices(index, 5, pitcher_matrix, __comp_matrix)
    elif score[0] == "a":
        lead = int(score[1:])
        lead = 10 if lead > 4 else lead + 5
        pitcher_matrix, __comp_matrix = __iter_indices(index, lead, pitcher_matrix, __comp_matrix)
    else:
        deficit = int(score[1:])
        deficit = 0 if deficit > 4 else np.abs(deficit - 5)
        pitcher_matrix, __comp_matrix = __iter_indices(index, deficit, pitcher_matrix, __comp_matrix)
    return pitcher_matrix, __comp_matrix


def __iter_indices(inning, lead, pitcher_matrix, __comp_matrix):
    pitcher_matrix[inning][lead] += 1
    __comp_matrix[inning][lead] += 1
    return pitcher_matrix, __comp_matrix


def __pitches_to_file(games, complete_refresh):
    if not complete_refresh:
        with open(os.path.join(cwd, "Pitcher Pitches.csv")) as file:
            pitches = {line.strip().split(",")[0].strip(): line.strip().split(",")[1:] for line in file.readlines()}
    else:
        pitches = {}

    # Iterate through yesterday's box scores, and add the pitch counts from all the pitchers who pitched
    for i, game in enumerate(games):
        game = game[1]
        box = requests.get(f"https://statsapi.mlb.com/api/v1/game/{game}/boxscore").json()
        for team_des in box["teams"]:
            team = box["teams"][team_des]
            for player_id in team["players"]:
                player = team["players"][player_id]
                if "numberOfPitches" in player["stats"]["pitching"]:
                    if player["person"]["fullName"] in pitches:
                        pitches[player["person"]["fullName"]].append(player["stats"]["pitching"]["numberOfPitches"])
                    else:
                        pitches[player["person"]["fullName"]] = [player["stats"]["pitching"]["numberOfPitches"]]

    with open(os.path.join(cwd, "Pitcher Pitches.csv"), 'w+') as file:
        for pitcher in pitches:
            file.write(f"{pitcher},")
            file_pitches = ",".join([str(pitch) for pitch in pitches[pitcher]])
            file.write(f"{file_pitches}\n")


__teams = {
    "Braves": "ATL",
    "Marlins": "MIA",
    "Mets": "NYM",
    "Phillies": "PHI",
    "Nationals": "WSN",
    "Cubs": "CHC",
    "Reds": "CIN",
    "Brewers": "MIL",
    "Pirates": "PIT",
    "Cardinals": "STL",
    "D-backs": "ARI",
    "Rockies": "COL",
    "Dodgers": "LAD",
    "Padres": "SDP",
    "Giants": "SFG",
    "Orioles": "BAL",
    "Red Sox": "BOS",
    "Yankees": "NYY",
    "Rays": "TBR",
    "Blue Jays": "TOR",
    "White Sox": "CHW",
    "Indians": "CLE",
    "Tigers": "DET",
    "Royals": "KCR",
    "Twins": "MIN",
    "Astros": "HOU",
    "Angels": "LAA",
    "Athletics": "OAK",
    "Mariners": "SEA",
    "Rangers": "TEX"
}
name_corrections = {
    "J.D. Hammer": "JD Hammer",
    "Josh Smith": "Josh A. Smith"
}
cwd = os.getcwd()
